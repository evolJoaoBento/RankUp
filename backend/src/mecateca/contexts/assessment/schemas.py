from __future__ import annotations

import uuid

from pydantic import BaseModel


class StartPracticeIn(BaseModel):
    subject: str
    concept: str | None = None
    difficulty: int = 2
    count: int = 5


class ItemOut(BaseModel):
    id: uuid.UUID
    concept_id: uuid.UUID
    kind: str
    difficulty: int
    payload: dict
    ordinal: int


class PracticeSessionOut(BaseModel):
    id: uuid.UUID
    subject_version_id: uuid.UUID
    difficulty: int
    items: list[ItemOut]


class AnswerIn(BaseModel):
    # mcq: {"selected_index": 1} ; reasoning/short: {"text": "..."}
    raw: dict


class AnswerResult(BaseModel):
    correct: bool
    reasoning_score: float
    feedback: str
    xp_delta: int
    xp_total: int
    rank: str
    ranked_up: bool
    streak: int
    already_answered: bool = False
    # mcq only, revealed AFTER answering: which option was right and why —
    # immediate corrective feedback is where the learning happens
    answer_index: int | None = None
    why: str = ""
