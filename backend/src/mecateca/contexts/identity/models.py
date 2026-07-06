from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class User(PkMixin, TimestampMixin, Base):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, default=None)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="student")  # student|teacher|admin
    display_name: Mapped[str] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(8), default="pt-PT")
    plan: Mapped[str] = mapped_column(String(16), default="free")  # free|pro
    background: Mapped[str | None] = mapped_column(String(32), default=None)  # chosen rank-colour theme
    avatar: Mapped[str] = mapped_column(String(24), default="")  # preset SVG avatar key ("" = initial)
    photo: Mapped[str] = mapped_column(String(40), default="")   # AI-moderated uploaded photo filename ("" = none)


class RefreshToken(PkMixin, TimestampMixin, Base):
    __tablename__ = "refresh_token"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)


class LoginAttempt(PkMixin, Base):
    """One row per login POST, per IP — backs cross-instance login rate limiting."""

    __tablename__ = "login_attempt"
    __table_args__ = (Index("ix_login_attempt_ip_created", "ip", "created_at"),)

    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
