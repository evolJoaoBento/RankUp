from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class TutorSession(PkMixin, TimestampMixin, Base):
    __tablename__ = "tutor_session"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE")
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("concept.id", ondelete="SET NULL"), default=None
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(160), default="Nova conversa")
    status: Mapped[str] = mapped_column(String(16), default="open")
    # soft delete: hidden from the user when set; hard-purged after the grace window
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)


class TutorMessage(PkMixin, TimestampMixin, Base):
    __tablename__ = "tutor_message"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tutor_session.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str] = mapped_column(String(48), default="")
