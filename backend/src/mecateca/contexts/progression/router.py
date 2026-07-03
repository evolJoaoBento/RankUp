from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity.models import User
from mecateca.contexts.progression import service
from mecateca.db.session import get_db
from mecateca.deps import current_user, require_role
from mecateca.shared.errors import NotFound

router = APIRouter(tags=["progression"])


class AdminEpIn(BaseModel):
    subject: str  # any discipline key — nothing is philosophy-specific
    xp: int


class TierIn(BaseModel):
    name: str
    ep: int


class SetTiersIn(BaseModel):
    profile: str = "standard"
    tiers: list[TierIn]


@router.get("/me/progress/{subject}")
async def my_progress(subject: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.progress(db, user.id, subject)


@router.get("/leaderboards/{subject}", dependencies=[Depends(current_user)])
async def leaderboard(
    subject: str, limit: int = Query(20, le=100), db: AsyncSession = Depends(get_db)
):
    return await service.leaderboard(db, subject, limit)


@router.get("/me/progress/{subject}/history")
async def my_xp_history(subject: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.xp_history(db, user.id, subject)


@router.get("/leaderboards/{subject}/me")
async def leaderboard_me(subject: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.my_position(db, subject, user.id) or {"position": None}


@router.get("/ranks", dependencies=[Depends(current_user)])
async def ranks(profile: str = "standard", db: AsyncSession = Depends(get_db)):
    from mecateca.contexts.progression import tiers as tiers_mod
    return [
        {"name": n, "ep": ep, "ordinal": i}
        for i, (n, ep) in enumerate(await tiers_mod.get_tiers(db, profile))
    ]


@router.patch("/admin/users/{user_id}/progress", dependencies=[Depends(require_role("admin"))])
async def admin_set_ep(user_id: uuid.UUID, body: AdminEpIn, db: AsyncSession = Depends(get_db)):
    if await db.get(User, user_id) is None:
        raise NotFound("user not found")
    return await service.admin_set_ep(db, user_id, body.subject, body.xp)


@router.patch("/admin/ranks", dependencies=[Depends(require_role("admin"))])
async def admin_set_ranks(body: SetTiersIn, db: AsyncSession = Depends(get_db)):
    from mecateca.contexts.progression import tiers as tiers_mod
    tiers = await tiers_mod.set_tiers(db, body.profile, [t.model_dump() for t in body.tiers])
    await tiers_mod.recompute_all_ranks(db)
    return [{"name": n, "ep": ep, "ordinal": i} for i, (n, ep) in enumerate(tiers)]
