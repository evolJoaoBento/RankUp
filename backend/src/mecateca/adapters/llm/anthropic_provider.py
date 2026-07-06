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

    async def moderate_image(self, data: bytes, media_type: str) -> tuple[bool, str]:
        """Claude vision moderation. Fails CLOSED on any error."""
        import base64

        try:
            resp = await self._client.messages.create(
                model=model_for("grade_reasoning"),
                max_tokens=200,
                system=(
                    "És um moderador de fotos de perfil de uma app escolar (alunos dos 10 aos 18). "
                    "Aprova apenas imagens apropriadas: retratos, desenhos, animais, paisagens, objetos neutros. "
                    "Rejeita: nudez/sugestivo, violência, armas, drogas/álcool/tabaco, símbolos de ódio, "
                    "texto ofensivo, informação pessoal visível. Responde APENAS com JSON: "
                    '{"approved": true|false, "reason": "curta"}'
                ),
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                 "data": base64.b64encode(data).decode()}},
                    {"type": "text", "text": "Modera esta foto de perfil."},
                ]}],
            )
            text = next((b.text for b in resp.content if b.type == "text"), "{}")
            verdict = json.loads(text)
            return bool(verdict.get("approved")), str(verdict.get("reason", ""))
        except Exception:
            return False, "moderação indisponível — tenta mais tarde"
