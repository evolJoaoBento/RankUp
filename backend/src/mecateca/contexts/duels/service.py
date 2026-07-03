from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from sqlalchemy import or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.adapters.llm.base import LLMProvider
from mecateca.contexts.catalog import service as catalog_service
from mecateca.contexts.catalog.models import Material
from mecateca.contexts.duels import elo, judge as judge_mod
from mecateca.contexts.duels.models import (
    ANSWER_SECS,
    DRAW_POINTS,
    QUESTION_SECS,
    TOTAL_ROUNDS,
    WIN_POINTS,
    Duel,
    DuelQueue,
    DuelRating,
    DuelRound,
)
from mecateca.contexts.identity.models import User
from mecateca.contexts.metering import service as metering
from mecateca.contexts.social import service as social_service
from mecateca.shared.clock import now
from mecateca.shared.errors import AppError, Forbidden, NotFound


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _other(duel: Duel, user_id: uuid.UUID) -> uuid.UUID:
    return duel.opponent_id if user_id == duel.challenger_id else duel.challenger_id


def _is_participant(duel: Duel, user_id: uuid.UUID) -> bool:
    return user_id in (duel.challenger_id, duel.opponent_id)


async def _owned(db: AsyncSession, duel_id: uuid.UUID, user: User) -> Duel:
    duel = await db.get(Duel, duel_id)
    if duel is None:
        raise NotFound("duelo não encontrado")
    if not _is_participant(duel, user.id):
        raise Forbidden("não fazes parte deste duelo")
    return duel


async def _round(db: AsyncSession, duel: Duel) -> DuelRound | None:
    return (
        await db.execute(
            select(DuelRound).where(
                DuelRound.duel_id == duel.id, DuelRound.ordinal == duel.current_round
            )
        )
    ).scalar_one_or_none()


async def _validate_material(db: AsyncSession, duel: Duel, material_id: uuid.UUID) -> Material:
    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material não encontrado")
    if m.subject_version_id != duel.subject_version_id:
        raise AppError("o material não pertence à disciplina do duelo")
    return m


# --------------------------------------------------------------------------- #
# lifecycle: invite / setup
# --------------------------------------------------------------------------- #
async def create(db: AsyncSession, challenger: User, opponent_id: uuid.UUID, subject_key: str) -> Duel:
    if opponent_id == challenger.id:
        raise AppError("não te podes desafiar a ti próprio")
    opponent = await db.get(User, opponent_id)
    if opponent is None:
        raise NotFound("adversário não encontrado")
    if not await social_service.are_friends(db, challenger.id, opponent_id):
        raise Forbidden("só podes desafiar amigos")
    sv = await catalog_service.current_version(db, subject_key)
    duel = Duel(
        subject_version_id=sv.id,
        challenger_id=challenger.id,
        opponent_id=opponent_id,
        status="pending",
    )
    db.add(duel)
    await db.flush()
    return duel


async def accept(db: AsyncSession, user: User, duel_id: uuid.UUID) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status != "pending":
        raise AppError("este duelo já não está pendente")
    if user.id != duel.opponent_id:
        raise Forbidden("só o adversário pode aceitar")
    duel.status = "setup"
    await db.flush()
    return duel


async def decline(db: AsyncSession, user: User, duel_id: uuid.UUID) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status not in ("pending", "setup"):
        raise AppError("este duelo já não pode ser recusado")
    duel.status = "declined"
    await db.flush()
    return duel


# leaving is consequence-free while the invite is unanswered, and for a short
# grace window right after it's accepted; after that only forfeit remains.
CANCEL_GRACE_SECS = 3


async def cancel(db: AsyncSession, user: User, duel_id: uuid.UUID) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.ranked:
        raise AppError("duelos ranked não podem ser cancelados")
    if duel.status == "pending":
        if user.id != duel.challenger_id:
            raise Forbidden("só quem desafiou pode cancelar o convite")
    elif duel.status == "setup":
        accepted_at = duel.updated_at or duel.created_at
        if (now() - accepted_at).total_seconds() > CANCEL_GRACE_SECS:
            raise AppError("o duelo já está bloqueado — só podes desistir")
    else:
        raise AppError("este duelo já não pode ser cancelado")
    duel.status = "cancelled"
    duel.phase = ""
    duel.phase_deadline = None
    await db.flush()
    return duel


async def pick_material(db: AsyncSession, user: User, duel_id: uuid.UUID, material_id: uuid.UUID) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status != "setup":
        raise AppError("ainda não é hora de escolher material")
    await _validate_material(db, duel, material_id)
    if user.id == duel.challenger_id:
        duel.challenger_material_id = material_id
    else:
        duel.opponent_material_id = material_id
    await db.flush()
    if duel.challenger_material_id and duel.opponent_material_id:
        await _start(db, duel)
    return duel


async def _start(db: AsyncSession, duel: Duel) -> None:
    duel.first_user_id = secrets.choice([duel.challenger_id, duel.opponent_id])  # coin flip
    duel.status = "active"
    duel.current_round = 0
    await _begin_round(db, duel, 0)


async def _begin_round(db: AsyncSession, duel: Duel, ordinal: int) -> None:
    # asker alternates: even rounds -> first_user, odd rounds -> the other
    asker = duel.first_user_id if ordinal % 2 == 0 else _other(duel, duel.first_user_id)
    rnd = DuelRound(duel_id=duel.id, ordinal=ordinal, asker_id=asker)
    db.add(rnd)
    duel.current_round = ordinal
    duel.phase = "question"
    duel.phase_deadline = now() + timedelta(seconds=QUESTION_SECS)
    await db.flush()


# --------------------------------------------------------------------------- #
# play: question / answer
# --------------------------------------------------------------------------- #
async def submit_question(db: AsyncSession, user: User, duel_id: uuid.UUID, text: str) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status != "active" or duel.phase != "question":
        raise AppError("não é a fase de criar pergunta")
    rnd = await _round(db, duel)
    if rnd is None or rnd.asker_id != user.id:
        raise Forbidden("não és quem cria a pergunta nesta ronda")
    text = (text or "").strip()
    if not text:
        raise AppError("escreve a pergunta")
    rnd.question_text = text[:4000]
    duel.phase = "answer"
    duel.phase_deadline = now() + timedelta(seconds=ANSWER_SECS)
    await db.flush()
    return duel


async def submit_answer(
    db: AsyncSession, provider: LLMProvider, user: User, duel_id: uuid.UUID, text: str
) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status != "active" or duel.phase != "answer":
        raise AppError("não é a fase de responder")
    rnd = await _round(db, duel)
    if rnd is None:
        raise AppError("ronda inválida")
    text = (text or "").strip()[:6000]
    if user.id == duel.challenger_id:
        if rnd.challenger_answered:
            raise AppError("já respondeste")
        rnd.challenger_answer = text
        rnd.challenger_answered = True
    else:
        if rnd.opponent_answered:
            raise AppError("já respondeste")
        rnd.opponent_answer = text
        rnd.opponent_answered = True
    await db.flush()
    if rnd.challenger_answered and rnd.opponent_answered:
        await _judge_round(db, provider, duel, rnd)
    return duel


async def forfeit(db: AsyncSession, user: User, duel_id: uuid.UUID) -> Duel:
    duel = await _owned(db, duel_id, user)
    if duel.status not in ("setup", "active"):
        raise AppError("este duelo já terminou")
    duel.status = "forfeited"
    duel.forfeited_by = user.id
    duel.winner_id = _other(duel, user.id)
    duel.phase = ""
    duel.phase_deadline = None
    await _apply_elo(db, duel)
    await db.flush()
    return duel


# --------------------------------------------------------------------------- #
# judging + advancing
# --------------------------------------------------------------------------- #
async def _judge_round(db: AsyncSession, provider: LLMProvider, duel: Duel, rnd: DuelRound) -> None:
    # atomic claim: only one request gets to judge this round
    claim = await db.execute(
        update(DuelRound)
        .where(DuelRound.id == rnd.id, DuelRound.verdict == "")
        .values(verdict="judging")
    )
    if claim.rowcount == 0:
        return  # another request is already judging / has judged
    duel.phase = "judging"
    await db.flush()

    asker_is_challenger = rnd.asker_id == duel.challenger_id
    if asker_is_challenger:
        a1, a2 = rnd.challenger_answer, rnd.opponent_answer
        material_id = duel.challenger_material_id
    else:
        a1, a2 = rnd.opponent_answer, rnd.challenger_answer
        material_id = duel.opponent_material_id

    reference = None
    if material_id:
        mat = await db.get(Material, material_id)
        if mat:
            reference = await catalog_service.material_full_text(db, mat)

    winner, reason, usage = await judge_mod.judge_answers(provider, rnd.question_text, a1, a2, reference)
    if usage:
        await metering.record(db, rnd.asker_id, "duel_judge", usage, ref_id=rnd.id)

    # map "1"/"2" (asker/responder) back to challenger/opponent
    if winner == "draw":
        side = "draw"
    elif winner == "1":
        side = "challenger" if asker_is_challenger else "opponent"
    else:
        side = "opponent" if asker_is_challenger else "challenger"

    rnd.reason = reason
    await _award_and_advance(db, duel, rnd, side)


async def _award_and_advance(db: AsyncSession, duel: Duel, rnd: DuelRound, side: str) -> None:
    if side == "draw":
        rnd.challenger_delta = rnd.opponent_delta = DRAW_POINTS
    elif side == "challenger":
        rnd.challenger_delta, rnd.opponent_delta = WIN_POINTS, 0
    else:
        rnd.challenger_delta, rnd.opponent_delta = 0, WIN_POINTS
    rnd.verdict = side
    duel.challenger_points += rnd.challenger_delta
    duel.opponent_points += rnd.opponent_delta
    await db.flush()

    if duel.current_round + 1 < TOTAL_ROUNDS:
        await _begin_round(db, duel, duel.current_round + 1)
    else:
        await _finish(db, duel)


async def _finish(db: AsyncSession, duel: Duel) -> None:
    duel.status = "complete"
    duel.phase = ""
    duel.phase_deadline = None
    if duel.challenger_points > duel.opponent_points:
        duel.winner_id = duel.challenger_id
    elif duel.opponent_points > duel.challenger_points:
        duel.winner_id = duel.opponent_id
    else:
        duel.winner_id = None  # draw
    await _apply_elo(db, duel)
    await db.flush()


async def _tick(db: AsyncSession, provider: LLMProvider, duel: Duel) -> None:
    """Resolve expired deadlines lazily (called on every read/action)."""
    if duel.status != "active" or duel.phase in ("", "judging"):
        return
    if duel.phase_deadline is None or now() < duel.phase_deadline:
        return
    rnd = await _round(db, duel)
    if rnd is None:
        return
    if duel.phase == "question" and not rnd.question_text:
        # asker ran out of time to author a question -> the responder takes the round
        rnd.question_text = "(sem pergunta — tempo esgotado)"
        rnd.reason = "Tempo esgotado para criar a pergunta."
        side = "opponent" if rnd.asker_id == duel.challenger_id else "challenger"
        await _award_and_advance(db, duel, rnd, side)
    elif duel.phase == "answer":
        # time's up: judge with whatever was submitted (missing = empty)
        await _judge_round(db, provider, duel, rnd)


# --------------------------------------------------------------------------- #
# views
# --------------------------------------------------------------------------- #
async def _names(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    rows = (await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))).all()
    return {i: n for i, n in rows}


async def _subject_meta(db: AsyncSession, duel: Duel) -> tuple[str, str]:
    from mecateca.contexts.catalog.models import Subject, SubjectVersion

    sv = await db.get(SubjectVersion, duel.subject_version_id)
    subj = await db.get(Subject, sv.subject_id) if sv else None
    return (subj.key if subj else ""), (subj.name if subj else "")


def _seconds_left(duel: Duel) -> int | None:
    if duel.phase_deadline is None:
        return None
    return max(0, int((duel.phase_deadline - now()).total_seconds()))


async def get_view(db: AsyncSession, provider: LLMProvider, user: User, duel_id: uuid.UUID) -> dict:
    duel = await _owned(db, duel_id, user)
    await _tick(db, provider, duel)

    me_is_challenger = user.id == duel.challenger_id
    names = await _names(db, [duel.challenger_id, duel.opponent_id])
    subj_key, subj_name = await _subject_meta(db, duel)

    my_points = duel.challenger_points if me_is_challenger else duel.opponent_points
    opp_points = duel.opponent_points if me_is_challenger else duel.challenger_points
    my_material = duel.challenger_material_id if me_is_challenger else duel.opponent_material_id
    opp_material = duel.opponent_material_id if me_is_challenger else duel.challenger_material_id

    rounds = list(
        (
            await db.execute(
                select(DuelRound).where(DuelRound.duel_id == duel.id).order_by(DuelRound.ordinal)
            )
        ).scalars()
    )
    cur = next((r for r in rounds if r.ordinal == duel.current_round), None)

    # current-round live state (redacted: opponent's answer hidden until judged)
    current = None
    if duel.status == "active" and cur is not None:
        i_am_asker = cur.asker_id == user.id
        my_answered = cur.challenger_answered if me_is_challenger else cur.opponent_answered
        opp_answered = cur.opponent_answered if me_is_challenger else cur.challenger_answered
        my_answer = cur.challenger_answer if me_is_challenger else cur.opponent_answer
        current = {
            "ordinal": cur.ordinal,
            "i_am_asker": i_am_asker,
            "asker_name": names.get(cur.asker_id, "?"),
            "question": cur.question_text if duel.phase in ("answer", "judging") else "",
            "my_answered": my_answered,
            "opp_answered": opp_answered,
            "my_answer": my_answer,
        }

    # finished rounds (full reveal)
    history = []
    for r in rounds:
        if r.verdict in ("", "judging"):
            continue
        if r.verdict == "draw":
            outcome = "draw"
        elif (r.verdict == "challenger") == me_is_challenger:
            outcome = "win"
        else:
            outcome = "loss"
        history.append({
            "ordinal": r.ordinal,
            "asker_name": names.get(r.asker_id, "?"),
            "question": r.question_text,
            "my_answer": r.challenger_answer if me_is_challenger else r.opponent_answer,
            "opp_answer": r.opponent_answer if me_is_challenger else r.challenger_answer,
            "outcome": outcome,
            "reason": r.reason,
            "my_delta": r.challenger_delta if me_is_challenger else r.opponent_delta,
            "opp_delta": r.opponent_delta if me_is_challenger else r.challenger_delta,
        })

    result = None
    if duel.status in ("complete", "forfeited"):
        if duel.winner_id is None:
            result = "draw"
        elif duel.winner_id == user.id:
            result = "win"
        else:
            result = "loss"

    return {
        "id": str(duel.id),
        "status": duel.status,
        "subject": subj_key,
        "subject_name": subj_name,
        "my_role": "challenger" if me_is_challenger else "opponent",
        "opponent_name": names.get(_other(duel, user.id), "?"),
        "opponent_id": str(_other(duel, user.id)),
        "my_name": names.get(user.id, "?"),
        "my_points": my_points,
        "opp_points": opp_points,
        "my_material_id": str(my_material) if my_material else None,
        "my_material_title": (
            (await db.get(Material, my_material)).title if my_material else None
        ),
        "opp_material_picked": opp_material is not None,
        "current_round": duel.current_round,
        "total_rounds": TOTAL_ROUNDS,
        "phase": duel.phase,
        "phase_deadline": duel.phase_deadline.isoformat() if duel.phase_deadline else None,
        "seconds_left": _seconds_left(duel),
        "current": current,
        "history": history,
        "result": result,
        "forfeited": duel.status == "forfeited",
        "i_forfeited": duel.forfeited_by == user.id if duel.forfeited_by else False,
        "ranked": duel.ranked,
        "rating_delta": (
            (duel.challenger_rating_delta if me_is_challenger else duel.opponent_rating_delta)
            if (duel.ranked and duel.status in ("complete", "forfeited")) else None
        ),
    }


async def list_duels(db: AsyncSession, user: User) -> list[dict]:
    duels = list(
        (
            await db.execute(
                select(Duel)
                .where(or_(Duel.challenger_id == user.id, Duel.opponent_id == user.id))
                .order_by(Duel.created_at.desc())
                .limit(40)
            )
        ).scalars()
    )
    names = await _names(db, [d.challenger_id for d in duels] + [d.opponent_id for d in duels])
    out = []
    for d in duels:
        me_is_challenger = user.id == d.challenger_id
        out.append({
            "id": str(d.id),
            "status": d.status,
            "opponent_name": names.get(_other(d, user.id), "?"),
            "my_points": d.challenger_points if me_is_challenger else d.opponent_points,
            "opp_points": d.opponent_points if me_is_challenger else d.challenger_points,
            "is_challenger": me_is_challenger,
            "needs_my_action": (
                (d.status == "pending" and not me_is_challenger)
                or (d.status == "setup" and not (
                    d.challenger_material_id if me_is_challenger else d.opponent_material_id))
                or d.status == "active"
            ),
            "won": d.winner_id == user.id if d.status in ("complete", "forfeited") else None,
            "is_draw": d.status == "complete" and d.winner_id is None,
            "ranked": d.ranked,
        })
    return out


# --------------------------------------------------------------------------- #
# ranked: Elo ratings + matchmaking
# --------------------------------------------------------------------------- #
MATCH_BASE_WINDOW = 100      # acceptable rating gap at t=0
MATCH_WINDOW_PER_10S = 60    # widens while waiting, so everyone eventually matches


def _match_window(wait_s: int) -> int:
    return MATCH_BASE_WINDOW + MATCH_WINDOW_PER_10S * (wait_s // 10)


async def _get_rating(db: AsyncSession, user_id: uuid.UUID) -> DuelRating:
    r = await db.get(DuelRating, user_id)
    if r is None:
        r = DuelRating(user_id=user_id, rating=elo.START_RATING)
        db.add(r)
        await db.flush()
    return r


async def _apply_elo(db: AsyncSession, duel: Duel) -> None:
    if not duel.ranked or duel.challenger_rating_delta or duel.opponent_rating_delta:
        return  # not ranked, or already applied
    ra = await _get_rating(db, duel.challenger_id)
    rb = await _get_rating(db, duel.opponent_id)
    old_a, old_b = ra.rating, rb.rating
    if duel.winner_id == duel.challenger_id:
        sa = 1.0
    elif duel.winner_id == duel.opponent_id:
        sa = 0.0
    else:
        sa = 0.5
    na, nb = elo.update(old_a, old_b, sa)
    ra.rating, rb.rating = na, nb
    ra.games += 1
    rb.games += 1
    if sa == 1.0:
        ra.wins += 1; rb.losses += 1
    elif sa == 0.0:
        ra.losses += 1; rb.wins += 1
    else:
        ra.draws += 1; rb.draws += 1
    duel.challenger_rating_delta = na - old_a
    duel.opponent_rating_delta = nb - old_b


async def rating_view(db: AsyncSession, user: User) -> dict:
    r = await _get_rating(db, user.id)
    return {"rating": r.rating, "games": r.games, "wins": r.wins, "losses": r.losses, "draws": r.draws}


async def leaderboard(db: AsyncSession, top: int = 20) -> list[dict]:
    rows = (
        await db.execute(
            select(DuelRating, User.display_name)
            .join(User, User.id == DuelRating.user_id)
            .where(DuelRating.games > 0)
            .order_by(DuelRating.rating.desc())
            .limit(top)
        )
    ).all()
    return [
        {"name": n, "rating": r.rating, "wins": r.wins, "losses": r.losses, "draws": r.draws}
        for r, n in rows
    ]


async def _open_ranked_duel(db: AsyncSession, user_id: uuid.UUID) -> Duel | None:
    return (
        await db.execute(
            select(Duel)
            .where(
                Duel.ranked.is_(True),
                or_(Duel.challenger_id == user_id, Duel.opponent_id == user_id),
                Duel.status.in_(("setup", "active")),
            )
            .order_by(Duel.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _try_match(db: AsyncSession, user_id: uuid.UUID, sv_id: uuid.UUID) -> Duel | None:
    # serialize matchmaking per discipline so two concurrent pollers can't double-pair
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": sv_id.int & 0x7FFFFFFF})
    me = await db.get(DuelQueue, user_id)
    if me is None:
        return None
    cands = list(
        (
            await db.execute(
                select(DuelQueue).where(
                    DuelQueue.subject_version_id == sv_id, DuelQueue.user_id != user_id
                )
            )
        ).scalars()
    )
    if not cands:
        return None
    best = min(cands, key=lambda c: abs(c.rating - me.rating))
    my_wait = int((now() - me.created_at).total_seconds())
    their_wait = int((now() - best.created_at).total_seconds())
    if abs(best.rating - me.rating) > max(_match_window(my_wait), _match_window(their_wait)):
        return None
    duel = Duel(
        subject_version_id=sv_id, challenger_id=user_id, opponent_id=best.user_id,
        status="setup", ranked=True,
    )
    db.add(duel)
    await db.delete(me)
    await db.delete(best)
    await db.flush()
    return duel


async def join_queue(db: AsyncSession, user: User, subject_key: str) -> dict:
    sv = await catalog_service.current_version(db, subject_key)
    existing = await _open_ranked_duel(db, user.id)
    if existing is not None:
        return {"state": "matched", "duel_id": str(existing.id)}
    r = await _get_rating(db, user.id)
    q = await db.get(DuelQueue, user.id)
    if q is not None:
        q.subject_version_id = sv.id
        q.rating = r.rating
    else:
        db.add(DuelQueue(user_id=user.id, subject_version_id=sv.id, rating=r.rating))
    await db.flush()
    duel = await _try_match(db, user.id, sv.id)
    return {"state": "matched", "duel_id": str(duel.id)} if duel else {"state": "queued", "waited": 0}


async def queue_status(db: AsyncSession, user: User) -> dict:
    duel = await _open_ranked_duel(db, user.id)
    if duel is not None:
        return {"state": "matched", "duel_id": str(duel.id)}
    q = await db.get(DuelQueue, user.id)
    if q is None:
        return {"state": "idle"}
    duel = await _try_match(db, user.id, q.subject_version_id)
    if duel is not None:
        return {"state": "matched", "duel_id": str(duel.id)}
    return {"state": "queued", "waited": int((now() - q.created_at).total_seconds())}


async def leave_queue(db: AsyncSession, user: User) -> None:
    q = await db.get(DuelQueue, user.id)
    if q is not None:
        await db.delete(q)
        await db.flush()
