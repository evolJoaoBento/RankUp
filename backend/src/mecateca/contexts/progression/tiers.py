from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.progression.models import RankTier, UserSubjectProgress
from mecateca.contexts.progression.rules import load_profile

Tier = tuple[str, int]  # (name, ep)


async def get_tiers(db: AsyncSession, profile_key: str = "standard") -> list[Tier]:
    rows = list(
        (
            await db.execute(
                select(RankTier).where(RankTier.profile_key == profile_key).order_by(RankTier.ordinal)
            )
        ).scalars()
    )
    if rows:
        return [(r.name, r.ep) for r in rows]
    return [(r.name, r.xp) for r in load_profile(profile_key).ranks]  # YAML fallback


def rank_for(tiers: list[Tier], xp: int) -> str:
    name = tiers[0][0]
    for n, ep in tiers:
        if xp >= ep:
            name = n
    return name


async def seed_tiers(db: AsyncSession, profile_key: str = "standard") -> None:
    existing = (
        await db.execute(select(RankTier).where(RankTier.profile_key == profile_key))
    ).first()
    if existing:
        return
    for i, r in enumerate(load_profile(profile_key).ranks):
        db.add(RankTier(profile_key=profile_key, name=r.name, ep=r.xp, ordinal=i))
    await db.flush()


async def reseed(db: AsyncSession, profile_key: str = "standard") -> list[Tier]:
    """Replace all tiers for a profile from the YAML defaults, then recompute ranks."""
    await db.execute(delete(RankTier).where(RankTier.profile_key == profile_key))
    await db.flush()
    await seed_tiers(db, profile_key)
    await recompute_all_ranks(db)
    return await get_tiers(db, profile_key)


async def set_tiers(db: AsyncSession, profile_key: str, items: list[dict]) -> list[Tier]:
    rows = {
        r.name: r
        for r in (
            await db.execute(select(RankTier).where(RankTier.profile_key == profile_key))
        ).scalars()
    }
    for it in items:
        row = rows.get(it["name"])
        if row is not None:
            row.ep = max(0, int(it["ep"]))
    await db.flush()
    return await get_tiers(db, profile_key)


async def recompute_all_ranks(db: AsyncSession) -> None:
    """After thresholds change, re-derive every user's stored rank."""
    from mecateca.contexts.catalog.models import Subject, SubjectVersion

    # map subject_id -> profile_key
    prof: dict = {}
    for s in (await db.execute(select(Subject))).scalars():
        sv = await db.get(SubjectVersion, s.current_version_id) if s.current_version_id else None
        prof[s.id] = sv.progression_profile if sv else "standard"
    cache: dict[str, list[Tier]] = {}
    for p in (await db.execute(select(UserSubjectProgress))).scalars():
        pk = prof.get(p.subject_id, "standard")
        if pk not in cache:
            cache[pk] = await get_tiers(db, pk)
        p.rank = rank_for(cache[pk], p.xp)
    await db.flush()
