from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from mecateca.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    s = get_settings()
    return create_async_engine(s.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)
