from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class UsageEvent(PkMixin, TimestampMixin, Base):
    __tablename__ = "usage_event"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # tutor_message | grade_reasoning | ...
    model: Mapped[str] = mapped_column(String(48))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_micro_eur: Mapped[int] = mapped_column(BigInteger, default=0)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
