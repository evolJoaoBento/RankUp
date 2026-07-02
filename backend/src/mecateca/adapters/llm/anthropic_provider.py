from __future__ import annotations

import json
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from mecateca.adapters.llm.base import LLMProvider, LLMRequest, Usage
from mecateca.adapters.llm.router import model_for


def _system_blocks(system: str) -> list[dict]:
    # Stable prefix -> cache it (~0.1x cost on repeat within a session).
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def _messages(req: LLMRequest) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in req.messages]


class _AnthropicStream:
    def __init__(self, client: AsyncAnthropic, model: str, req: LLMRequest):
        self._client = client
        self._model = model
        self._req = req
        self.usage: Usage | None = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self._run()

    async def _run(self) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._req.max_tokens,
            system=_system_blocks(self._req.system),
            messages=_messages(self._req),
        ) as stream:
            async for text in stream.text_stream:
                yield text
            final = await stream.get_final_message()
        self.usage = Usage(final.usage.input_tokens, final.usage.output_tokens, self._model)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)

    async def stream(self, req: LLMRequest) -> _AnthropicStream:
        return _AnthropicStream(self._client, model_for(req.task), req)

    async def parse(self, req: LLMRequest, json_schema: dict) -> tuple[dict, Usage]:
        model = model_for(req.task)
        resp = await self._client.messages.create(
            model=model,
            max_tokens=req.max_tokens,
            system=_system_blocks(req.system),
            messages=_messages(req),
            output_config={"format": {"type": "json_schema", "schema": json_schema}},
        )
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        usage = Usage(resp.usage.input_tokens, resp.usage.output_tokens, model)
        return json.loads(text), usage
