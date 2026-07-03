from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin

# ---- tuning ----
ROUNDS_PER_PLAYER = 2
TOTAL_ROUNDS = ROUNDS_PER_PLAYER * 2  # each player asks twice -> 4 rounds
QUESTION_SECS = 120                   # phase to author the question
ANSWER_SECS = 180                     # phase where BOTH answer simultaneously

WIN_POINTS = 2
DRAW_POINTS = 1


class Duel(PkMixin, TimestampMixin, Base):
    __tablename__ = "duel"

    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE")
    )
    challenger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    opponent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)

    # pending | setup | active | complete | declined | forfeited | cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)

    challenger_material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material.id", ondelete="SET NULL"), default=None
    )
    opponent_material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material.id", ondelete="SET NULL"), default=None
    )

    first_user_id: Mapped[uuid.UUID | None] = mapped_column(default=None)  # coin-flip: asker of round 0
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(16), default="")  # question | answer | judging | ""
    phase_deadline: Mapped[datetime | None] = mapped_column(default=None)

    challenger_points: Mapped[int] = mapped_column(Integer, default=0)
    opponent_points: Mapped[int] = mapped_column(Integer, default=0)

    winner_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    forfeited_by: Mapped[uuid.UUID | None] = mapped_column(default=None)

    ranked: Mapped[bool] = mapped_column(Boolean, default=False)
    challenger_rating_delta: Mapped[int] = mapped_column(Integer, default=0)
    opponent_rating_delta: Mapped[int] = mapped_column(Integer, default=0)


class DuelRating(TimestampMixin, Base):
    """One Elo row per player PER DISCIPLINE — being good at Maths says nothing
    about Philosophy (chess-style, K=32)."""

    __tablename__ = "duel_rating"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[int] = mapped_column(Integer, default=1000)
    games: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)


class DuelQueue(TimestampMixin, Base):
    """A player waiting for a ranked match in a given discipline."""

    __tablename__ = "duel_queue"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer, default=1000)


class DuelRound(PkMixin, TimestampMixin, Base):
    __tablename__ = "duel_round"

    duel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("duel.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    asker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))

    question_text: Mapped[str] = mapped_column(Text, default="")
    challenger_answer: Mapped[str] = mapped_column(Text, default="")
    opponent_answer: Mapped[str] = mapped_column(Text, default="")
    challenger_answered: Mapped[bool] = mapped_column(default=False)
    opponent_answered: Mapped[bool] = mapped_column(default=False)

    # "" (unjudged) | judging | challenger | opponent | draw
    verdict: Mapped[str] = mapped_column(String(16), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    challenger_delta: Mapped[int] = mapped_column(Integer, default=0)
    opponent_delta: Mapped[int] = mapped_column(Integer, default=0)
