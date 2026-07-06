from __future__ import annotations

from fastapi import APIRouter, Depends, Request, UploadFile
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
    UpdateMeIn,
    UpdateUserIn,
    UserOut,
)
from mecateca.db.session import get_db
from mecateca.deps import current_user, get_llm_provider, require_role
from mecateca.shared.errors import AppError, Forbidden, NotFound

router = APIRouter(tags=["identity"])


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(body: RegisterIn, request: Request, db: AsyncSession = Depends(get_db)):
    # same Postgres-backed IP throttle as login — stops mass account creation
    await service.check_login_rate(request.client.host if request.client else "?")
    user = await service.register(db, body.email, body.password, body.display_name)
    return user


@router.post("/auth/login", response_model=TokenPair)
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "?"
    await service.check_login_rate(ip)
    tokens = await service.authenticate(db, body.identifier, body.password)
    await service.clear_login_attempts(ip)  # success resets the window (shared/NAT IPs)
    return tokens


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    return await service.refresh(db, body.refresh)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(body: UpdateMeIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.update_me(db, user, body.display_name, body.username, body.avatar)


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


# ---- profile photo (uploaded, AI-moderated) ----
_PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_PHOTO_MAX = 2 * 1024 * 1024  # 2 MB
_PHOTO_MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _photo_dir():
    from pathlib import Path

    from mecateca.config import get_settings

    d = Path(get_settings().upload_dir) / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/me/photo", response_model=UserOut)
async def upload_photo(
    file: UploadFile,
    user: User = Depends(current_user),
    provider=Depends(get_llm_provider),
    db: AsyncSession = Depends(get_db),
):
    ext = _PHOTO_TYPES.get(file.content_type or "")
    if ext is None:
        raise AppError("formato inválido — usa JPEG, PNG ou WebP")
    data = await file.read()
    if len(data) > _PHOTO_MAX:
        raise AppError("imagem demasiado grande (máx. 2 MB)")
    approved, reason = await provider.moderate_image(data, file.content_type)
    if not approved:
        raise AppError(f"foto recusada pela moderação: {reason}", code="moderation")
    name = f"{user.id}.{ext}"
    for old_ext in _PHOTO_TYPES.values():  # one photo per user, regardless of format
        p = _photo_dir() / f"{user.id}.{old_ext}"
        if p.exists():
            p.unlink()
    (_photo_dir() / name).write_bytes(data)
    user.photo = name
    await db.flush()
    return user


@router.delete("/me/photo", response_model=UserOut)
async def delete_photo(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.photo:
        p = _photo_dir() / user.photo
        if p.exists():
            p.unlink()
        user.photo = ""
        await db.flush()
    return user


@router.get("/users/{user_id}/photo")
async def get_photo(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import FileResponse

    u = await db.get(User, user_id)
    if u is None or not u.photo:
        raise NotFound("sem foto")
    p = _photo_dir() / u.photo
    if not p.exists():
        raise NotFound("sem foto")
    return FileResponse(p, media_type=_PHOTO_MIME.get(u.photo.rsplit(".", 1)[-1], "image/jpeg"),
                        headers={"Cache-Control": "public, max-age=300"})


# ---- admin: platform overview ----
@router.get("/admin/stats", dependencies=[Depends(require_role("admin"))])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func

    from mecateca.contexts.catalog.models import Material, Subject, Test
    from mecateca.contexts.duels.models import Duel
    from mecateca.contexts.tutoring.models import TutorSession

    async def count(model, *where):
        q = select(func.count()).select_from(model)
        for w in where:
            q = q.where(w)
        return (await db.execute(q)).scalar_one()

    return {
        "users": await count(User),
        "teachers": await count(User, User.role == "teacher"),
        "subjects": await count(Subject),
        "materials": await count(Material),
        "materials_pending": await count(Material, Material.teacher_approved.is_(False)),
        "tests": await count(Test),
        "conversations": await count(TutorSession, TutorSession.deleted_at.is_(None)),
        "deleted_conversations": await count(TutorSession, TutorSession.deleted_at.is_not(None)),
        "duels": await count(Duel),
    }


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
