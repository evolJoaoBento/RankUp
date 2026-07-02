from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

# Force the offline FakeProvider for tests (no Ollama/Claude needed).
os.environ["MECATECA_LLM_BACKEND"] = "fake"
# CRITICAL: isolate tests on a dedicated database — pytest must NEVER touch the dev DB.
_TEST_DB = os.environ.get("MECATECA_TEST_DB", "mecateca_test")
os.environ["MECATECA_DATABASE_URL"] = (
    f"postgresql+asyncpg://mecateca:mecateca@localhost:5432/{_TEST_DB}"
)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from mecateca.db.base import Base  # noqa: E402
from mecateca.db.engine import get_engine, get_sessionmaker  # noqa: E402
from mecateca.db import registry  # noqa: E402,F401
from mecateca.contexts.catalog.pack_loader import load_from_path  # noqa: E402
from mecateca.main import app  # noqa: E402

PACK = Path(__file__).resolve().parents[1] / "packs" / "philosophy" / "1.0.0" / "pack.yaml"


async def _ensure_test_db() -> None:
    """Create the dedicated test database if missing (connect via the dev DB)."""
    import asyncpg
    sys_conn = await asyncpg.connect(
        user="mecateca", password="mecateca", host="localhost", port=5432, database="mecateca"
    )
    try:
        exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", _TEST_DB)
        if not exists:
            await sys_conn.execute(f'CREATE DATABASE "{_TEST_DB}"')
    finally:
        await sys_conn.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _schema():
    await _ensure_test_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)   # safe: this is the isolated test DB
        await conn.run_sync(Base.metadata.create_all)
    sm = get_sessionmaker()
    async with sm() as db:
        await load_from_path(db, PACK)
        await db.commit()
    yield
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(loop_scope="session")
async def auth(client):
    email = f"u{uuid.uuid4().hex[:10]}@test.dev"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pw12345678", "display_name": "Test"},
    )
    r = await client.post("/api/v1/auth/login", json={"identifier": email, "password": "pw12345678"})
    token = r.json()["access"]
    return {"authorization": f"Bearer {token}"}
