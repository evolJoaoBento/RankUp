from __future__ import annotations

import uuid

from pydantic import BaseModel


class StartSessionIn(BaseModel):
    subject: str
    material: str | None = None  # material id to ground the session
    concept: str | None = None   # legacy; optional


class SessionOut(BaseModel):
    id: uuid.UUID
    subject_version_id: uuid.UUID
    material_id: uuid.UUID | None
    title: str
    status: str


class SessionListItem(BaseModel):
    id: uuid.UUID
    title: str
    material_id: uuid.UUID | None


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
