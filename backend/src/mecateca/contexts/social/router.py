from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity.models import User
from mecateca.contexts.social import service
from mecateca.contexts.social.schemas import FriendRequestIn, FriendsView, MessageIn, MessageOut
from mecateca.db.session import get_db
from mecateca.deps import current_user

router = APIRouter(tags=["social"])


@router.get("/friends", response_model=FriendsView)
async def list_friends(subject: str | None = None, user: User = Depends(current_user),
                       db: AsyncSession = Depends(get_db)):
    return await service.overview(db, user, subject)


@router.post("/friends/requests", response_model=FriendsView)
async def send_request(body: FriendRequestIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.send_request(db, user, body.identifier, body.user_id)
    return await service.overview(db, user)


@router.post("/friends/requests/{req_id}/accept", response_model=FriendsView)
async def accept(req_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.accept(db, user, req_id)
    return await service.overview(db, user)


@router.post("/friends/requests/{req_id}/decline", response_model=FriendsView)
async def decline(req_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.decline(db, user, req_id)
    return await service.overview(db, user)


# ---- people: search + public profiles ----
@router.get("/users/search")
async def search_users(q: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.search_users(db, user, q)


@router.get("/users/{other_id}/profile")
async def public_profile(
    other_id: uuid.UUID, subject: str | None = None,
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db),
):
    return await service.public_profile(db, user, other_id, subject)


# ---- direct messages (friends only) ----
def _msg_out(m) -> MessageOut:
    return MessageOut(id=m.id, from_id=m.from_id, text=m.text, created_at=m.created_at.isoformat())


@router.get("/messages/unread")
async def unread(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.unread(db, user)


@router.get("/messages/{other_id}", response_model=list[MessageOut])
async def thread(other_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return [_msg_out(m) for m in await service.thread(db, user, other_id)]


@router.post("/messages/{other_id}", response_model=MessageOut)
async def send(other_id: uuid.UUID, body: MessageIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return _msg_out(await service.send_message(db, user, other_id, body.text))


@router.delete("/friends/{other_id}", response_model=FriendsView)
async def remove(other_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.remove_friend(db, user, other_id)
    return await service.overview(db, user)
