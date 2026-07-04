from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity import service as identity_service
from mecateca.contexts.identity.models import User
from mecateca.contexts.social.models import Friendship
from mecateca.shared.errors import AppError, Conflict, NotFound


async def _between(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> Friendship | None:
    return (
        await db.execute(
            select(Friendship).where(
                or_(
                    (Friendship.requester_id == a) & (Friendship.addressee_id == b),
                    (Friendship.requester_id == b) & (Friendship.addressee_id == a),
                )
            )
        )
    ).scalar_one_or_none()


async def are_friends(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> bool:
    f = await _between(db, a, b)
    return f is not None and f.status == "accepted"


async def send_request(db: AsyncSession, me: User, identifier: str) -> Friendship:
    target = await identity_service.get_by_identifier(db, identifier)
    if target is None:
        raise NotFound("utilizador não encontrado")
    if target.id == me.id:
        raise AppError("não te podes adicionar a ti próprio")
    existing = await _between(db, me.id, target.id)
    if existing is not None:
        if existing.status == "accepted":
            raise Conflict("já são amigos")
        # a pending request the other way around -> accept it
        if existing.addressee_id == me.id:
            existing.status = "accepted"
            await db.flush()
            return existing
        raise Conflict("pedido já enviado")
    f = Friendship(requester_id=me.id, addressee_id=target.id, status="pending")
    db.add(f)
    await db.flush()
    return f


async def accept(db: AsyncSession, me: User, req_id: uuid.UUID) -> Friendship:
    f = await db.get(Friendship, req_id)
    if f is None or f.addressee_id != me.id or f.status != "pending":
        raise NotFound("pedido não encontrado")
    f.status = "accepted"
    await db.flush()
    return f


async def decline(db: AsyncSession, me: User, req_id: uuid.UUID) -> None:
    f = await db.get(Friendship, req_id)
    if f is None or f.addressee_id != me.id or f.status != "pending":
        raise NotFound("pedido não encontrado")
    await db.delete(f)
    await db.flush()


async def remove_friend(db: AsyncSession, me: User, other_id: uuid.UUID) -> None:
    f = await _between(db, me.id, other_id)
    if f is None:
        raise NotFound("não são amigos")
    await db.delete(f)
    await db.flush()


async def _users(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars()
    return {u.id: u for u in rows}


async def overview(db: AsyncSession, me: User) -> dict:
    rows = list(
        (
            await db.execute(
                select(Friendship).where(
                    or_(Friendship.requester_id == me.id, Friendship.addressee_id == me.id)
                )
            )
        ).scalars()
    )
    other_ids = [r.requester_id if r.addressee_id == me.id else r.addressee_id for r in rows]
    users = await _users(db, other_ids)

    friends, incoming, outgoing = [], [], []
    for r in rows:
        other_id = r.requester_id if r.addressee_id == me.id else r.addressee_id
        u = users.get(other_id)
        if u is None:
            continue
        if r.status == "accepted":
            friends.append({"user_id": u.id, "display_name": u.display_name,
                            "username": u.username, "avatar": u.avatar})
        elif r.addressee_id == me.id:
            incoming.append({"id": r.id, "user_id": u.id, "display_name": u.display_name,
                             "username": u.username, "direction": "incoming"})
        else:
            outgoing.append({"id": r.id, "user_id": u.id, "display_name": u.display_name,
                             "username": u.username, "direction": "outgoing"})
    friends.sort(key=lambda f: f["display_name"].lower())
    return {"friends": friends, "incoming": incoming, "outgoing": outgoing}


# --------------------------------------------------------------------------- #
# direct messages (friends only)
# --------------------------------------------------------------------------- #
from mecateca.contexts.social.models import DirectMessage  # noqa: E402
from mecateca.shared.clock import now  # noqa: E402

MAX_MSG_LEN = 500
THREAD_LIMIT = 50


async def send_message(db: AsyncSession, me: User, other_id: uuid.UUID, text: str) -> DirectMessage:
    text = text.strip()
    if not text:
        raise AppError("escreve uma mensagem")
    if len(text) > MAX_MSG_LEN:
        raise AppError("mensagem demasiado longa")
    if not await are_friends(db, me.id, other_id):
        raise AppError("só podes enviar mensagens a amigos", code="forbidden", status_code=403)
    msg = DirectMessage(from_id=me.id, to_id=other_id, text=text)
    db.add(msg)
    await db.flush()
    return msg


async def thread(db: AsyncSession, me: User, other_id: uuid.UUID) -> list[DirectMessage]:
    """Last messages between me and a friend; reading marks their side as read."""
    if not await are_friends(db, me.id, other_id):
        raise AppError("só podes ver conversas com amigos", code="forbidden", status_code=403)
    msgs = list(
        (
            await db.execute(
                select(DirectMessage)
                .where(
                    or_(
                        (DirectMessage.from_id == me.id) & (DirectMessage.to_id == other_id),
                        (DirectMessage.from_id == other_id) & (DirectMessage.to_id == me.id),
                    )
                )
                .order_by(DirectMessage.created_at.desc())
                .limit(THREAD_LIMIT)
            )
        ).scalars()
    )[::-1]
    for m in msgs:
        if m.to_id == me.id and m.read_at is None:
            m.read_at = now()
    await db.flush()
    return msgs


async def unread(db: AsyncSession, me: User) -> dict:
    from sqlalchemy import func

    rows = (
        await db.execute(
            select(DirectMessage.from_id, func.count())
            .where(DirectMessage.to_id == me.id, DirectMessage.read_at.is_(None))
            .group_by(DirectMessage.from_id)
        )
    ).all()
    by_user = {str(uid): int(n) for uid, n in rows}
    return {"total": sum(by_user.values()), "by_user": by_user}
