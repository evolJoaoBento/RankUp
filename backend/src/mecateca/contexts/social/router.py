from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity.models import User
from mecateca.contexts.social import service
from mecateca.contexts.social.schemas import FriendRequestIn, FriendsView
from mecateca.db.session import get_db
from mecateca.deps import current_user

router = APIRouter(tags=["social"])


@router.get("/friends", response_model=FriendsView)
async def list_friends(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await service.overview(db, user)


@router.post("/friends/requests", response_model=FriendsView)
async def send_request(body: FriendRequestIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.send_request(db, user, body.identifier)
    return await service.overview(db, user)


@router.post("/friends/requests/{req_id}/accept", response_model=FriendsView)
async def accept(req_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.accept(db, user, req_id)
    return await service.overview(db, user)


@router.post("/friends/requests/{req_id}/decline", response_model=FriendsView)
async def decline(req_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.decline(db, user, req_id)
    return await service.overview(db, user)


@router.delete("/friends/{other_id}", response_model=FriendsView)
async def remove(other_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.remove_friend(db, user, other_id)
    return await service.overview(db, user)
