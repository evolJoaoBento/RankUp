from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator

import httpx

from mecateca.adapters.llm.base import LLMProvider, LLMRequest, Usage


def _messages(req: LLMRequest) -> list[dict]:
    msgs = [{"role": "system", "content": req.system}]
    msgs += [{"role": m.role, "content": m.content} for m in req.messages]
    return msgs


def _usage(model: str, data: dict | None) -> Usage:
    u = (data or {}).get("usage") or {}
    return Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), model)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


class _GatewayStream:
    def __init__(self, base_url: str, model: str | None, req: LLMRequest):
        self._url = f"{base_url}/chat/completions"
        self._model = model
        self._req = req
        self.usage: Usage | None = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self._run()

    async def _run(self) -> AsyncIterator[str]:
        body: dict = {"messages": _messages(self._req), "stream": True}
        if self._model:
            body["model"] = self._model
        out_chars = 0
        last: dict | None = None
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self._url, json=body,
                                     headers={"authorization": "Bearer local"}) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    last = obj
                    delta = (obj.get("choices") or [{}])[0].get("delta", {})
                    chunk = delta.get("content")
                    if chunk:
                        out_chars += len(chunk)
                        yield chunk
        u = (last or {}).get("usage")
        if u:
            self.usage = _usage(self._model or "claude-gateway", last)
        else:
            self.usage = Usage(0, max(1, out_chars // 4), self._model or "claude-gateway")


class GatewayProvider(LLMProvider):
    """OpenAI-compatible local gateway -> Claude Code CLI (user's plan, no API billing)."""

    def __init__(self, base_url: str, model: str | None = None):
        self._base = base_url.rstrip("/")
        self._model = model or None

    async def stream(self, req: LLMRequest) -> _GatewayStream:
        return _GatewayStream(self._base, self._model, req)

    async def parse(self, req: LLMRequest, json_schema: dict) -> tuple[dict, Usage]:
        sys = (
            req.system
            + "\n\nResponde APENAS com JSON válido (sem markdown, sem texto extra) que obedeça a este schema:\n"
            + json.dumps(json_schema, ensure_ascii=False)
        )
        body: dict = {
            "messages": [{"role": "system", "content": sys}]
            + [{"role": m.role, "content": m.content} for m in req.messages],
            "stream": False,
        }
        if self._model:
            body["model"] = self._model
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{self._base}/chat/completions", json=body,
                                     headers={"authorization": "Bearer local"})
            resp.raise_for_status()
            data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "{}")
        return _extract_json(content), _usage(self._model or "claude-gateway", data)

    async def moderate_image(self, data: bytes, media_type: str) -> tuple[bool, str]:
        """Vision moderation via the LOCAL gateway: the OpenAI-compat endpoint is
        text-only, but the Claude CLI behind it can Read files — so we hand it a
        temp file path on this same machine. Fails CLOSED on any doubt."""
        import os
        import tempfile

        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(media_type, ".img")
        fd, path = tempfile.mkstemp(suffix=ext, prefix="rankup_moderate_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            body: dict = {
                "messages": [
                    {"role": "system", "content": (
                        "És um moderador de fotos de perfil de uma app escolar (alunos dos 10 aos 18). "
                        "Aprova apenas imagens apropriadas: retratos, desenhos, animais, paisagens, objetos neutros. "
                        "Rejeita: nudez/sugestivo, violência, armas, drogas/álcool/tabaco, símbolos de ódio, "
                        "texto ofensivo, informação pessoal visível. Se não conseguires ver a imagem, "
                        'rejeita. Responde APENAS com JSON: {"approved": true|false, "reason": "curta"}'
                    )},
                    {"role": "user", "content": (
                        f"Lê a imagem no ficheiro {path} (usa a ferramenta Read) e modera-a como foto de perfil. "
                        "Responde só com o JSON."
                    )},
                ],
                "stream": False,
            }
            if self._model:
                body["model"] = self._model
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(f"{self._base}/chat/completions", json=body,
                                         headers={"authorization": "Bearer local"})
                resp.raise_for_status()
                content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
            verdict = _extract_json(content)
            return bool(verdict.get("approved")), str(verdict.get("reason", ""))
        except Exception:
            return False, "moderação indisponível — tenta mais tarde"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
