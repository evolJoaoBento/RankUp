from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.config import get_settings
from mecateca.contexts.metering.models import UsageEvent
from mecateca.shared.clock import now
from mecateca.shared.errors import QuotaExceeded


async def tutor_messages_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    since = now() - timedelta(days=1)
    res = await db.execute(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.user_id == user_id,
            UsageEvent.kind == "tutor_message",
            UsageEvent.created_at >= since,
        )
    )
    return int(res.scalar_one())


async def check_tutor(db: AsyncSession, user_id: uuid.UUID, plan: str) -> None:
    if plan != "free":
        return
    cap = get_settings().free_tutor_msgs_per_day
    if await tutor_messages_today(db, user_id) >= cap:
        raise QuotaExceeded(
            f"free plan tutor limit reached ({cap}/day). Upgrade to Pro.",
            code="tutor_quota",
        )


async def remaining_tutor(db: AsyncSession, user_id: uuid.UUID, plan: str) -> int | None:
    if plan != "free":
        return None
    cap = get_settings().free_tutor_msgs_per_day
    return max(0, cap - await tutor_messages_today(db, user_id))
