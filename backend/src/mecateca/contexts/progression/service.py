from __future__ import annotations

import uuid

from sqlalchemy import desc, select
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

    weak = list(
        (
            await db.execute(
                select(UserConceptMastery)
                .where(UserConceptMastery.user_id == user_id)
                .order_by(UserConceptMastery.mastery.asc())
                .limit(5)
            )
        ).scalars()
    )
    return {
        "subject": subject_key,
        "xp": prog.xp if prog else 0,
        "rank": prog.rank if prog else lowest,
        "streak": prog.streak if prog else 0,
        "weak_concepts": [
            {"concept_id": str(w.concept_id), "mastery": float(w.mastery)} for w in weak
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
