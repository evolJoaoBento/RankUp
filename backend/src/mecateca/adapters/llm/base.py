from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMRequest:
    task: str  # "tutor_socratic" | "grade_reasoning" | "generate_question"
    system: str
    messages: list[LLMMessage] = field(default_factory=list)
    max_tokens: int = 1024


@dataclass
class Usage:
    tokens_in: int
    tokens_out: int
    model: str


class ProviderStream(Protocol):
    """Async-iterable of text chunks; `.usage` populated once fully consumed."""

    usage: Usage | None

    def __aiter__(self) -> AsyncIterator[str]: ...


@runtime_checkable
class LLMProvider(Protocol):
    async def stream(self, req: LLMRequest) -> ProviderStream: ...
    async def parse(self, req: LLMRequest, json_schema: dict) -> tuple[dict, Usage]: ...

    async def moderate_image(self, data: bytes, media_type: str) -> tuple[bool, str]:
        """(approved, reason). Providers without vision must FAIL CLOSED."""
        ...
