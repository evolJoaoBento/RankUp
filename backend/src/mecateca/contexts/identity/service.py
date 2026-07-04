from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.config import get_settings
from mecateca.contexts.identity import security
from mecateca.contexts.identity.models import LoginAttempt, RefreshToken, User
from mecateca.contexts.identity.schemas import TokenPair
from mecateca.shared.clock import now
from mecateca.shared.errors import AppError, Conflict, Unauthorized

LOGIN_RATE_WINDOW_S = 300  # 5 min
LOGIN_RATE_MAX = 10        # attempts per IP per window


async def check_login_rate(ip: str) -> None:
    """Postgres-backed login throttle — shared across app instances (replaces the
    old per-process in-memory counter). Raises 429 once the window is exhausted.

    Runs in its own committed session so the attempt is recorded even when the
    login then fails and the request transaction rolls back (brute-force = repeated
    failures must still count)."""
    from mecateca.db.engine import get_sessionmaker

    cutoff = now() - timedelta(seconds=LOGIN_RATE_WINDOW_S)
    async with get_sessionmaker()() as db:
        await db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))  # prune
        n = await db.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(LoginAttempt.ip == ip, LoginAttempt.created_at >= cutoff)
        )
        if (n or 0) >= LOGIN_RATE_MAX:
            raise AppError(
                "Demasiadas tentativas. Tenta mais tarde.",
                code="rate_limited",
                status_code=429,
            )
        db.add(LoginAttempt(ip=ip))
        await db.commit()


async def clear_login_attempts(ip: str) -> None:
    """A successful login proves the client isn't brute-forcing — reset its window.
    Without this, a shared IP (school NAT) locks a whole classroom out after 10
    perfectly valid logins."""
    from mecateca.db.engine import get_sessionmaker

    async with get_sessionmaker()() as db:
        await db.execute(delete(LoginAttempt).where(LoginAttempt.ip == ip))
        await db.commit()


async def update_me(
    db: AsyncSession, user: User,
    display_name: str | None, username: str | None, avatar: str | None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip()
    if username is not None:
        uname = username.strip().lower()
        taken = (
            await db.execute(select(User).where(User.username == uname, User.id != user.id))
        ).scalar_one_or_none()
        if taken is not None:
            raise Conflict("esse nome de utilizador já está ocupado")
        user.username = uname
    if avatar is not None:
        user.avatar = avatar.strip()
    await db.flush()
    return user


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    res = await db.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()


async def get_by_identifier(db: AsyncSession, ident: str) -> User | None:
    ident = ident.strip().lower()
    res = await db.execute(
        select(User).where((User.email == ident) | (User.username == ident))
    )
    return res.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def register(db: AsyncSession, email: str, password: str, display_name: str) -> User:
    if await get_by_email(db, email):
        raise Conflict("email already registered", code="email_taken")
    user = User(
        email=email.lower(),
        password_hash=security.hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    await db.flush()
    return user


async def _issue_tokens(db: AsyncSession, user: User) -> TokenPair:
    s = get_settings()
    access = security.make_access_token(user.id, user.role)
    raw_refresh = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=security.hash_token(raw_refresh),
            expires_at=now() + timedelta(days=s.jwt_refresh_ttl_days),
        )
    )
    await db.flush()
    return TokenPair(access=access, refresh=raw_refresh)


async def authenticate(db: AsyncSession, identifier: str, password: str) -> TokenPair:
    user = await get_by_identifier(db, identifier)
    if not user or not security.verify_password(password, user.password_hash):
        raise Unauthorized("invalid credentials", code="bad_credentials")
    # transparently upgrade the hash if argon2 params changed
    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
        await db.flush()
    return await _issue_tokens(db, user)


async def revoke_all_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    from sqlalchemy import update
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now())
    )


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if not security.verify_password(current, user.password_hash):
        raise Unauthorized("current password is wrong", code="bad_password")
    if security.verify_password(new, user.password_hash):
        raise Conflict("new password must differ", code="same_password")
    user.password_hash = security.hash_password(new)
    await revoke_all_tokens(db, user.id)  # force re-login everywhere
    await db.flush()


async def seed_admin(db: AsyncSession) -> None:
    """Ensure the bootstrap admin exists (username 'admin', password 'admin')."""
    existing = await get_by_identifier(db, "admin")
    if existing:
        return
    db.add(
        User(
            email="admin@mecateca.pt",
            username="admin",
            password_hash=security.hash_password("admin"),
            display_name="Admin",
            role="admin",
            plan="pro",
        )
    )
    await db.flush()


async def refresh(db: AsyncSession, raw_refresh: str) -> TokenPair:
    th = security.hash_token(raw_refresh)
    res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == th))
    row = res.scalar_one_or_none()
    if not row or row.revoked_at is not None or row.expires_at < now():
        raise Unauthorized("invalid refresh token", code="bad_refresh")
    row.revoked_at = now()  # rotate
    user = await get_by_id(db, row.user_id)
    assert user is not None
    return await _issue_tokens(db, user)
