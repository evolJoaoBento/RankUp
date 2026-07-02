from __future__ import annotations

import uuid
from functools import lru_cache

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.adapters.llm.anthropic_provider import AnthropicProvider
from mecateca.adapters.llm.base import LLMProvider
from mecateca.adapters.llm.fake_provider import FakeProvider
from mecateca.adapters.llm.gateway_provider import GatewayProvider
from mecateca.adapters.llm.ollama_provider import OllamaProvider
from mecateca.config import Settings, get_settings
from mecateca.contexts.identity import service as identity_service
from mecateca.contexts.identity.models import User
from mecateca.db.session import get_db
from mecateca.shared.errors import Forbidden, Unauthorized

_bearer = HTTPBearer(auto_error=False)


def settings() -> Settings:
    return get_settings()


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_backend == "fake":
        return FakeProvider()
    if s.llm_backend == "gateway":
        return GatewayProvider(s.gateway_base_url, s.gateway_model)
    if s.llm_backend == "anthropic":
        return AnthropicProvider(s.anthropic_api_key)
    return OllamaProvider(
        s.ollama_base_url, s.ollama_model, s.ollama_think, s.ollama_num_ctx, s.ollama_num_gpu
    )


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise Unauthorized("missing bearer token")
    try:
        payload = jwt.decode(
            creds.credentials, get_settings().jwt_secret, algorithms=[get_settings().jwt_alg]
        )
    except jwt.PyJWTError as exc:
        raise Unauthorized("invalid token") from exc
    if payload.get("type") != "access":
        raise Unauthorized("wrong token type")
    user = await identity_service.get_by_id(db, uuid.UUID(payload["sub"]))
    if user is None:
        raise Unauthorized("user not found")
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise Forbidden(f"requires role: {', '.join(roles)}")
        return user

    return _dep
