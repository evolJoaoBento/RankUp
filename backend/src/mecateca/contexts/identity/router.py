from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from sqlalchemy import select

from mecateca.contexts.identity import service
from mecateca.contexts.identity.models import User
from mecateca.contexts.identity.schemas import (
    AdminUserOut,
    BackgroundIn,
    ChangePasswordIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UpdateUserIn,
    UserOut,
)
from mecateca.db.session import get_db
from mecateca.deps import current_user, require_role
from mecateca.shared.errors import Forbidden, NotFound

router = APIRouter(tags=["identity"])


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    user = await service.register(db, body.email, body.password, body.display_name)
    return user


@router.post("/auth/login", response_model=TokenPair)
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    await service.check_login_rate(request.client.host if request.client else "?")
    return await service.authenticate(db, body.identifier, body.password)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    return await service.refresh(db, body.refresh)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user


@router.post("/me/password", status_code=204)
async def change_my_password(body: ChangePasswordIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.change_password(db, user, body.current_password, body.new_password)


@router.patch("/me/background", response_model=UserOut)
async def set_my_background(body: BackgroundIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.background:
        from mecateca.contexts.progression import service as prog_service
        from mecateca.contexts.progression import tiers as tiers_mod
        tiers = dict(await tiers_mod.get_tiers(db, "standard"))
        if body.background not in tiers:
            raise Forbidden("unknown rank")
        prog = await prog_service.progress(db, user.id, "philosophy")
        if prog["xp"] < tiers[body.background]:
            raise Forbidden("rank not unlocked")
    user.background = body.background or None
    await db.flush()
    return user


# ---- admin: account management ----
@router.get("/admin/users", response_model=list[AdminUserOut], dependencies=[Depends(require_role("admin"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(User).order_by(User.created_at))).scalars())


@router.patch("/admin/users/{user_id}", response_model=AdminUserOut, dependencies=[Depends(require_role("admin"))])
async def update_user(user_id: uuid.UUID, body: UpdateUserIn, db: AsyncSession = Depends(get_db)):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFound("user not found")
    if body.role is not None:
        if body.role not in ("student", "teacher", "admin"):
            raise Forbidden("invalid role")
        u.role = body.role
    if body.plan is not None:
        u.plan = body.plan
    if body.set_background:  # admin testing — no unlock check
        u.background = body.background or None
    await db.flush()
    return u


@router.delete("/admin/users/{user_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: uuid.UUID, admin: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    if user_id == admin.id:
        raise Forbidden("cannot delete yourself")
    u = await db.get(User, user_id)
    if u is None:
        raise NotFound("user not found")
    await db.delete(u)
