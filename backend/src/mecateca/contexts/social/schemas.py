from __future__ import annotations

import uuid

from pydantic import BaseModel


class FriendRequestIn(BaseModel):
    identifier: str  # email or username of the target user


class FriendOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    username: str | None = None


class FriendRequestOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID         # the other party
    display_name: str
    username: str | None = None
    direction: str             # "incoming" | "outgoing"


class FriendsView(BaseModel):
    friends: list[FriendOut]
    incoming: list[FriendRequestOut]
    outgoing: list[FriendRequestOut]
