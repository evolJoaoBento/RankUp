from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog import service as catalog_service
from mecateca.contexts.catalog.models import Material
from mecateca.contexts.identity.models import User
from mecateca.contexts.tutoring.models import TutorMessage, TutorSession
from mecateca.shared.clock import now
from mecateca.shared.errors import Forbidden, NotFound

# soft-deleted chats are recoverable for this long, then purged permanently
DELETE_GRACE_DAYS = 180  # ~6 months


async def start_session(
    db: AsyncSession, user_id: uuid.UUID, subject_key: str, material_id: str | None
) -> TutorSession:
    sv = await catalog_service.current_version(db, subject_key)
    mid = None
    title = "Tópico livre"
    if material_id:
        m = await db.get(Material, material_id)
        if m is None or m.subject_version_id != sv.id:
            raise NotFound("material not in subject")
        mid = m.id
        title = m.title
    session = TutorSession(
        user_id=user_id, subject_version_id=sv.id, material_id=mid, title=title
    )
    db.add(session)
    await db.flush()
    return session


async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[TutorSession]:
    return list(
        (
            await db.execute(
                select(TutorSession)
                .where(TutorSession.user_id == user_id, TutorSession.deleted_at.is_(None))
                .order_by(TutorSession.updated_at.desc())
            )
        ).scalars()
    )


async def get_owned(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> TutorSession:
    session = await db.get(TutorSession, session_id)
    if session is None or session.deleted_at is not None:
        raise NotFound("session not found")
    if session.user_id != user_id:
        raise Forbidden("not your session")
    return session


async def soft_delete(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Hide the chat now; it stays recoverable in the admin panel until purged."""
    session = await get_owned(db, user_id, session_id)
    session.deleted_at = now()
    await db.flush()


# ---- admin: recovery + purge ----
async def list_deleted(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(TutorSession, User.display_name, func.count(TutorMessage.id))
            .join(User, User.id == TutorSession.user_id)
            .outerjoin(TutorMessage, TutorMessage.session_id == TutorSession.id)
            .where(TutorSession.deleted_at.is_not(None))
            .group_by(TutorSession.id, User.display_name)
            .order_by(TutorSession.deleted_at.desc())
        )
    ).all()
    cutoff = now() - timedelta(days=DELETE_GRACE_DAYS)
    out = []
    for s, owner, n in rows:
        purge_at = s.deleted_at + timedelta(days=DELETE_GRACE_DAYS) if s.deleted_at else None
        out.append({
            "id": str(s.id),
            "title": s.title,
            "owner": owner,
            "messages": int(n),
            "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
            "purges_at": purge_at.isoformat() if purge_at else None,
            "expired": bool(s.deleted_at and s.deleted_at < cutoff),
        })
    return out


async def restore(db: AsyncSession, session_id: uuid.UUID) -> None:
    s = await db.get(TutorSession, session_id)
    if s is None or s.deleted_at is None:
        raise NotFound("deleted chat not found")
    s.deleted_at = None
    await db.flush()


async def purge_expired(db: AsyncSession) -> int:
    """Hard-delete chats soft-deleted longer than the grace window. Messages cascade."""
    cutoff = now() - timedelta(days=DELETE_GRACE_DAYS)
    res = await db.execute(
        delete(TutorSession).where(
            TutorSession.deleted_at.is_not(None),
            TutorSession.deleted_at < cutoff,
        )
    )
    return res.rowcount or 0
