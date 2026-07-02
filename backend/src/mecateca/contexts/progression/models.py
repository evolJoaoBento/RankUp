from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class RankTier(PkMixin, TimestampMixin, Base):
    __tablename__ = "rank_tier"
    __table_args__ = (UniqueConstraint("profile_key", "name"),)
    profile_key: Mapped[str] = mapped_column(String(64), index=True, default="standard")
    name: Mapped[str] = mapped_column(String(32))
    ep: Mapped[int] = mapped_column(Integer, default=0)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)


class Season(PkMixin, TimestampMixin, Base):
    __tablename__ = "season"
    subject_id: Mapped[uuid.UUID | None] = mapped_column(default=None)  # null = cross-subject
    key: Mapped[str] = mapped_column(String(64), index=True)
    starts_at: Mapped[datetime | None] = mapped_column(default=None)
    ends_at: Mapped[datetime | None] = mapped_column(default=None)


class ProgressionEvent(PkMixin, TimestampMixin, Base):
    __tablename__ = "progression_event"
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=False), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    season_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    type: Mapped[str] = mapped_column(String(40))  # AnswerGraded | XpAwarded | RankUp
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class UserSubjectProgress(TimestampMixin, Base):
    __tablename__ = "user_subject_progress"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    season_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[str] = mapped_column(String(32), default="Bronze")
    streak: Mapped[int] = mapped_column(Integer, default=0)


class UserConceptMastery(TimestampMixin, Base):
    __tablename__ = "user_concept_mastery"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concept.id", ondelete="CASCADE"), primary_key=True
    )
    mastery: Mapped[float] = mapped_column(Numeric(4, 3), default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
