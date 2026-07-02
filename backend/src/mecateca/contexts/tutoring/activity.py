from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.adapters.llm.base import LLMMessage, LLMProvider, LLMRequest, Usage
from mecateca.contexts.catalog.models import Material
from mecateca.contexts.tutoring.models import TutorMessage, TutorSession
from mecateca.contexts.tutoring.prompts import build_system

HISTORY_LIMIT = 20


class SocraticChatActivity:
    """Activity plugin: streams a Socratic reply, returns usage via callback."""

    type = "socratic_chat"

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    async def stream_reply(
        self, db: AsyncSession, session: TutorSession, user_text: str
    ) -> tuple[AsyncIterator[str], "list[str]", "_UsageHolder"]:
        concept = None
        # the session is grounded on a chosen material (if any), including its attachments
        materials = []
        if session.material_id:
            m = await db.get(Material, session.material_id)
            if m is not None:
                from mecateca.contexts.catalog import service as catalog_service
                full = await catalog_service.material_full_text(db, m)
                materials = [type("_Mat", (), {"title": m.title, "body": full})()]
        history = list(
            (
                await db.execute(
                    select(TutorMessage)
                    .where(TutorMessage.session_id == session.id)
                    .order_by(TutorMessage.created_at.desc())
                    .limit(HISTORY_LIMIT)
                )
            ).scalars()
        )[::-1]
        msgs = [LLMMessage(m.role, m.content) for m in history]
        msgs.append(LLMMessage("user", user_text))

        req = LLMRequest(task="tutor_socratic", system=build_system(concept, materials), messages=msgs)
        provider_stream = await self._provider.stream(req)

        collected: list[str] = []
        holder = _UsageHolder()

        async def gen() -> AsyncIterator[str]:
            async for chunk in provider_stream:
                collected.append(chunk)
                yield chunk
            holder.usage = provider_stream.usage

        return gen(), collected, holder


class _UsageHolder:
    usage: Usage | None = None
