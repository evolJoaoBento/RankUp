from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class PracticeSession(PkMixin, TimestampMixin, Base):
    __tablename__ = "practice_session"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE")
    )
    focus_concept_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="open")


class PracticeItem(PkMixin, TimestampMixin, Base):
    __tablename__ = "practice_item"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_session.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"))
    question_template_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    kind: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)


class Answer(PkMixin, TimestampMixin, Base):
    __tablename__ = "answer"
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_item.id", ondelete="CASCADE"), unique=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    grade: Mapped[dict] = mapped_column(JSONB, default=dict)
    reasoning_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    graded_by: Mapped[str] = mapped_column(String(24), default="")
