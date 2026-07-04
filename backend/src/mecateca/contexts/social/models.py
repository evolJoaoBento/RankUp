from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class Friendship(PkMixin, TimestampMixin, Base):
    """One row per relationship. `requester` sent the request to `addressee`.
    status: pending | accepted. Declines/removals delete the row."""

    __tablename__ = "friendship"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id"),)

    requester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    addressee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | accepted


class DirectMessage(PkMixin, TimestampMixin, Base):
    """Friend-to-friend chat. Only friends can message each other (school-safe)."""

    __tablename__ = "direct_message"
    __table_args__ = (Index("ix_dm_to_read", "to_id", "read_at"),)

    from_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    to_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(default=None)
