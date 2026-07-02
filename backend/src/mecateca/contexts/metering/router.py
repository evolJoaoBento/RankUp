from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.identity.models import User
from mecateca.contexts.metering import quota
from mecateca.contexts.metering.models import UsageEvent
from mecateca.db.session import get_db
from mecateca.deps import current_user

router = APIRouter(tags=["metering"])


@router.get("/me/usage")
async def my_usage(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.tokens_in), 0),
            func.coalesce(func.sum(UsageEvent.tokens_out), 0),
            func.coalesce(func.sum(UsageEvent.cost_micro_eur), 0),
        ).where(UsageEvent.user_id == user.id)
    )
    tin, tout, cost = res.one()
    return {
        "tokens_in": int(tin),
        "tokens_out": int(tout),
        "cost_eur": round(int(cost) / 1_000_000, 4),
        "tutor_messages_remaining_today": await quota.remaining_tutor(db, user.id, user.plan),
    }
