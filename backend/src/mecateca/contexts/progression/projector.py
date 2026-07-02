from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.progression.models import (
    ProgressionEvent,
    Season,
    UserConceptMastery,
    UserSubjectProgress,
)
from mecateca.contexts.progression import tiers as tiers_mod
from mecateca.contexts.progression.rules import load_profile
from mecateca.shared.clock import now

MASTERY_ALPHA = 0.3


@dataclass
class ProgressResult:
    xp_delta: int
    xp_total: int
    rank: str
    ranked_up: bool
    streak: int
    mastery: float


async def _default_season(db: AsyncSession) -> Season:
    row = (await db.execute(select(Season).where(Season.key == "all-time"))).scalar_one_or_none()
    if row is None:
        row = Season(key="all-time")
        db.add(row)
        await db.flush()
    return row


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


async def apply_answer_graded(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    correct: bool,
    reasoning_score: float,
    difficulty: int,
    profile_key: str = "standard",
    ep_award: int | None = None,
    ep_wrong: int | None = None,
) -> ProgressResult:
    profile = load_profile(profile_key)
    tiers = await tiers_mod.get_tiers(db, profile_key)
    season = await _default_season(db)

    prog = await db.get(UserSubjectProgress, (user_id, subject_id, season.id))
    if prog is None:
        prog = UserSubjectProgress(
            user_id=user_id, subject_id=subject_id, season_id=season.id, xp=0, rank=tiers[0][0]
        )
        db.add(prog)
        await db.flush()

    streak = prog.streak + 1 if correct else 0
    xp_delta = profile.xp_for(correct, reasoning_score, streak, ep_award, ep_wrong)  # per-question EP override
    prev_rank = prog.rank

    prog.streak = streak
    prog.xp = max(0, prog.xp + xp_delta)
    prog.rank = tiers_mod.rank_for(tiers, prog.xp)
    ranked_up = prog.rank != prev_rank

    # event log (append-only, source of truth)
    db.add(ProgressionEvent(
        user_id=user_id, subject_id=subject_id, season_id=season.id, type="AnswerGraded",
        payload={"concept_id": str(concept_id), "correct": correct,
                 "reasoning_score": reasoning_score, "difficulty": difficulty},
    ))
    if xp_delta:
        db.add(ProgressionEvent(
            user_id=user_id, subject_id=subject_id, season_id=season.id, type="XpAwarded",
            payload={"amount": xp_delta, "streak": streak},
        ))
    if ranked_up:
        db.add(ProgressionEvent(
            user_id=user_id, subject_id=subject_id, season_id=season.id, type="RankUp",
            payload={"from": prev_rank, "to": prog.rank},
        ))

    # mastery update (decay toward reasoning-weighted outcome)
    outcome = reasoning_score if correct else 0.0
    m = await db.get(UserConceptMastery, (user_id, concept_id))
    if m is None:
        m = UserConceptMastery(user_id=user_id, concept_id=concept_id, mastery=0)
        db.add(m)
    prior = float(m.mastery or 0)
    m.mastery = round(_clamp01(prior * (1 - MASTERY_ALPHA) + outcome * MASTERY_ALPHA), 3)
    m.last_seen_at = now()

    await db.flush()
    return ProgressResult(
        xp_delta=xp_delta, xp_total=prog.xp, rank=prog.rank,
        ranked_up=ranked_up, streak=streak, mastery=float(m.mastery),
    )
