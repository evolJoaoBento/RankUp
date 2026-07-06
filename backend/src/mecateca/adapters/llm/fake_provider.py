from __future__ import annotations

from collections.abc import AsyncIterator

from mecateca.adapters.llm.base import LLMProvider, LLMRequest, Usage
from mecateca.adapters.llm.router import model_for


def _est(text: str) -> int:
    return max(1, len(text) // 4)


class _FakeStream:
    def __init__(self, model: str, req: LLMRequest, reply: str):
        self._model = model
        self._req = req
        self._reply = reply
        self.usage: Usage | None = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self._run()

    async def _run(self) -> AsyncIterator[str]:
        for word in self._reply.split(" "):
            yield word + " "
        tin = _est(self._req.system) + sum(_est(m.content) for m in self._req.messages)
        self.usage = Usage(tin, _est(self._reply), self._model)


class FakeProvider(LLMProvider):
    """Deterministic, offline. Lets the whole app run without an API key."""

    async def stream(self, req: LLMRequest) -> _FakeStream:
        last = req.messages[-1].content if req.messages else ""
        reply = (
            "Boa pergunta. Não te dou a resposta — vamos pensar. "
            f"Sobre '{last[:60]}', qual é o teu palpite e porquê? "
            "O que já sabes que te pode ajudar aqui?"
        )
        return _FakeStream(model_for(req.task), req, reply)

    async def parse(self, req: LLMRequest, json_schema: dict) -> tuple[dict, Usage]:
        # Deterministic reasoning grade: reward length + presence of 'porque'/'because'.
        ans = req.messages[-1].content.lower() if req.messages else ""
        score = 0.0
        if len(ans) > 40:
            score += 0.5
        if any(w in ans for w in ("porque", "because", "logo", "portanto", "therefore")):
            score += 0.3
        if len(ans) > 120:
            score += 0.2
        score = min(1.0, score)
        data = {
            "correct": score >= 0.5,
            "reasoning_score": score,
            "feedback": "Avaliação simulada (FakeProvider): mostra mais o teu raciocínio.",
        }
        model = model_for(req.task)
        return data, Usage(_est(req.system) + _est(ans), 20, model)

    async def moderate_image(self, data: bytes, media_type: str) -> tuple[bool, str]:
        # deterministic for tests: any payload containing UNSAFE is rejected
        if b"UNSAFE" in data:
            return False, "conteudo impróprio (simulado)"
        return True, "ok (simulado)"
