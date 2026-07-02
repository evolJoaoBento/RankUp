from __future__ import annotations

import uuid

from pydantic import BaseModel


class CreateDuelIn(BaseModel):
    opponent_id: uuid.UUID
    subject: str


class PickMaterialIn(BaseModel):
    material_id: uuid.UUID


class QuestionIn(BaseModel):
    text: str


class AnswerIn(BaseModel):
    text: str = ""
