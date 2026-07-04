from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog import service as catalog_service
from mecateca.contexts.identity.models import User
from mecateca.contexts.progression.models import (
    Season,
    UserConceptMastery,
    UserSubjectProgress,
)


async def _all_time(db: AsyncSession) -> Season | None:
    return (await db.execute(select(Season).where(Season.key == "all-time"))).scalar_one_or_none()


async def admin_set_ep(db: AsyncSession, user_id: uuid.UUID, subject_key: str, xp: int) -> dict:
    """Set a user's EP; rank is always re-derived from the current tier thresholds."""
    from mecateca.contexts.catalog.models import SubjectVersion
    from mecateca.contexts.progression import tiers as tiers_mod
    from mecateca.contexts.progression.models import ProgressionEvent, UserSubjectProgress
    from mecateca.contexts.progression.projector import _default_season

    subject = await catalog_service.get_subject(db, subject_key)
    sv = await db.get(SubjectVersion, subject.current_version_id)
    tiers = await tiers_mod.get_tiers(db, sv.progression_profile if sv else "standard")

    season = await _default_season(db)
    prog = await db.get(UserSubjectProgress, (user_id, subject.id, season.id))
    if prog is None:
        prog = UserSubjectProgress(
            user_id=user_id, subject_id=subject.id, season_id=season.id, rank=tiers[0][0]
        )
        db.add(prog)
    prog.xp = max(0, int(xp))
    prog.rank = tiers_mod.rank_for(tiers, prog.xp)
    db.add(ProgressionEvent(
        user_id=user_id, subject_id=subject.id, season_id=season.id,
        type="AdminAdjust", payload={"xp": prog.xp, "rank": prog.rank},
    ))
    await db.flush()
    return {"xp": prog.xp, "rank": prog.rank}


async def progress(db: AsyncSession, user_id: uuid.UUID, subject_key: str) -> dict:
    from mecateca.contexts.catalog.models import SubjectVersion
    from mecateca.contexts.progression import tiers as tiers_mod

    subject = await catalog_service.get_subject(db, subject_key)
    sv = await db.get(SubjectVersion, subject.current_version_id) if subject.current_version_id else None
    tiers = await tiers_mod.get_tiers(db, sv.progression_profile if sv else "standard")
    lowest = tiers[0][0] if tiers else "Wood"
    season = await _all_time(db)
    prog = None
    if season is not None:
        prog = await db.get(UserSubjectProgress, (user_id, subject.id, season.id))

    from mecateca.contexts.catalog.models import Concept

    weak = (
        await db.execute(
            select(UserConceptMastery, Concept.name, Concept.key)
            .join(Concept, Concept.id == UserConceptMastery.concept_id)
            .where(
                UserConceptMastery.user_id == user_id,
                Concept.subject_version_id == subject.current_version_id,
            )
            .order_by(UserConceptMastery.mastery.asc())
            .limit(5)
        )
    ).all()

    from sqlalchemy import func as _f

    from mecateca.contexts.assessment.models import Answer
    answers_today = (
        await db.execute(
            select(_f.count()).select_from(Answer).where(
                Answer.user_id == user_id,
                Answer.created_at >= _f.date_trunc("day", _f.now()),
            )
        )
    ).scalar_one()

    return {
        "subject": subject_key,
        "xp": prog.xp if prog else 0,
        "rank": prog.rank if prog else lowest,
        "streak": prog.streak if prog else 0,
        "answers_today": int(answers_today),
        "weak_concepts": [
            {"concept_id": str(w.concept_id), "name": name, "key": key, "mastery": float(w.mastery)}
            for w, name, key in weak
        ],
    }


async def leaderboard(db: AsyncSession, subject_key: str, limit: int = 20) -> list[dict]:
    subject = await catalog_service.get_subject(db, subject_key)
    season = await _all_time(db)
    if season is None:
        return []
    rows = (
        await db.execute(
            select(UserSubjectProgress, User.display_name)
            .join(User, User.id == UserSubjectProgress.user_id)
            .where(
                UserSubjectProgress.subject_id == subject.id,
                UserSubjectProgress.season_id == season.id,
            )
            .order_by(desc(UserSubjectProgress.xp))
            .limit(limit)
        )
    ).all()
    return [
        {"display_name": name, "xp": p.xp, "rank": p.rank, "streak": p.streak}
        for p, name in rows
    ]


async def xp_history(db: AsyncSession, user_id, subject_key: str, days: int = 14) -> list[dict]:
    """EP earned per day (from the append-only event log) for a profile sparkline."""
    from datetime import timedelta

    from sqlalchemy import Integer, cast, func

    from mecateca.contexts.progression.models import ProgressionEvent
    from mecateca.shared.clock import now

    subject = await catalog_service.get_subject(db, subject_key)
    since = now() - timedelta(days=days - 1)
    day = func.date_trunc("day", ProgressionEvent.created_at)
    rows = (
        await db.execute(
            select(day, func.sum(cast(ProgressionEvent.payload["amount"].astext, Integer)))
            .where(
                ProgressionEvent.user_id == user_id,
                ProgressionEvent.subject_id == subject.id,
                ProgressionEvent.type == "XpAwarded",
                ProgressionEvent.created_at >= since,
            )
            .group_by(day)
            .order_by(day)
        )
    ).all()
    by_day = {d.date().isoformat(): int(s or 0) for d, s in rows}
    today = now().date()
    return [
        {"day": (today - timedelta(days=i)).isoformat(), "ep": by_day.get((today - timedelta(days=i)).isoformat(), 0)}
        for i in range(days - 1, -1, -1)
    ]


async def class_weak_topics(db: AsyncSession, subject_key: str, limit: int = 10) -> list[dict]:
    """Class-wide mastery per topic, weakest first — the teacher's radar."""
    from sqlalchemy import func

    from mecateca.contexts.catalog.models import Concept
    from mecateca.contexts.progression.models import UserConceptMastery

    subject = await catalog_service.get_subject(db, subject_key)
    sv_id = subject.current_version_id
    rows = (
        await db.execute(
            select(
                Concept.name,
                func.count(UserConceptMastery.user_id),
                func.avg(UserConceptMastery.mastery),
            )
            .join(UserConceptMastery, UserConceptMastery.concept_id == Concept.id)
            .where(Concept.subject_version_id == sv_id)
            .group_by(Concept.id, Concept.name)
            .order_by(func.avg(UserConceptMastery.mastery).asc())
            .limit(limit)
        )
    ).all()
    return [
        {"topic": name, "students": int(n), "avg_mastery": round(float(avg or 0), 2)}
        for name, n, avg in rows
    ]


async def my_position(db: AsyncSession, subject_key: str, user_id) -> dict | None:
    """1-based ladder position of the user in a subject, or None if unranked."""
    subject = await catalog_service.get_subject(db, subject_key)
    season = await _all_time(db)
    if season is None:
        return None
    prog = await db.get(UserSubjectProgress, (user_id, subject.id, season.id))
    if prog is None:
        return None
    higher = (
        await db.execute(
            select(func.count())
            .select_from(UserSubjectProgress)
            .where(
                UserSubjectProgress.subject_id == subject.id,
                UserSubjectProgress.season_id == season.id,
                UserSubjectProgress.xp > prog.xp,
            )
        )
    ).scalar_one()
    return {"position": higher + 1, "xp": prog.xp, "rank": prog.rank, "streak": prog.streak}
