from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from mecateca.adapters.llm.base import LLMProvider, LLMRequest, Usage


def _messages(req: LLMRequest) -> list[dict]:
    msgs = [{"role": "system", "content": req.system}]
    msgs += [{"role": m.role, "content": m.content} for m in req.messages]
    return msgs


def _options(num_predict: int, num_ctx: int, num_gpu: int) -> dict:
    opts = {"num_predict": num_predict, "num_ctx": num_ctx}
    if num_gpu >= 0:
        opts["num_gpu"] = num_gpu
    return opts


def _resolve_think(mode: str, model: str) -> bool | None:
    if mode == "on":
        return True
    if mode == "off":
        return False
    # auto: disable thinking for known thinking models so output stays clean
    return False if ("qwen3" in model or "deepseek-r1" in model) else None


class _OllamaStream:
    def __init__(self, base_url, model, req, think, num_ctx, num_gpu):
        self._url = f"{base_url}/api/chat"
        self._model = model
        self._req = req
        self._think = think
        self._num_ctx = num_ctx
        self._num_gpu = num_gpu
        self.usage: Usage | None = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self._run()

    async def _run(self) -> AsyncIterator[str]:
        body = {
            "model": self._model,
            "messages": _messages(self._req),
            "stream": True,
            "options": _options(self._req.max_tokens, self._num_ctx, self._num_gpu),
        }
        if self._think is not None:
            body["think"] = self._think
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self._url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    chunk = obj.get("message", {}).get("content")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        self.usage = Usage(
                            obj.get("prompt_eval_count", 0),
                            obj.get("eval_count", 0),
                            self._model,
                        )


class OllamaProvider(LLMProvider):
    """Local models via Ollama. Default model: llama3.1:8b. Structured grading needs Ollama >= 0.5."""

    def __init__(self, base_url, model, think_mode="auto", num_ctx=8192, num_gpu=-1):
        self._base = base_url.rstrip("/")
        self._model = model
        self._think = _resolve_think(think_mode, model)
        self._num_ctx = num_ctx
        self._num_gpu = num_gpu

    async def stream(self, req: LLMRequest) -> _OllamaStream:
        return _OllamaStream(self._base, self._model, req, self._think, self._num_ctx, self._num_gpu)

    async def moderate_image(self, data: bytes, media_type: str) -> tuple[bool, str]:
        # text-only local models can't judge images — FAIL CLOSED, never approve blindly
        return False, "moderação de imagens indisponível neste modelo"

    async def parse(self, req: LLMRequest, json_schema: dict) -> tuple[dict, Usage]:
        body = {
            "model": self._model,
            "messages": _messages(req),
            "stream": False,
            "format": json_schema,  # Ollama structured output (>= 0.5)
            "options": _options(req.max_tokens, self._num_ctx, self._num_gpu),
        }
        if self._think is not None:
            body["think"] = self._think
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self._base}/api/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "{}")
        usage = Usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0), self._model)
        return json.loads(content), usage
