from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.adapters.llm.base import Usage
from mecateca.contexts.metering.models import UsageEvent

# USD per 1M tokens (input, output). EUR conversion applied below.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}
USD_TO_EUR = 0.92


def cost_micro_eur(usage: Usage) -> int:
    price = PRICES.get(usage.model)
    if price is None:
        return 0  # local model (Ollama) — no API cost
    pin, pout = price
    usd = usage.tokens_in / 1_000_000 * pin + usage.tokens_out / 1_000_000 * pout
    return int(round(usd * USD_TO_EUR * 1_000_000))


async def record(
    db: AsyncSession, user_id: uuid.UUID, kind: str, usage: Usage, ref_id: uuid.UUID | None = None
) -> UsageEvent:
    ev = UsageEvent(
        user_id=user_id,
        kind=kind,
        model=usage.model,
        tokens_in=usage.tokens_in,
        tokens_out=usage.tokens_out,
        cost_micro_eur=cost_micro_eur(usage),
        ref_id=ref_id,
    )
    db.add(ev)
    await db.flush()
    return ev
