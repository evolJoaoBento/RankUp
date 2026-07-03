from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'"
)
# Postgres advisory-lock key: serializes startup (migrations + seed) across instances.
_STARTUP_LOCK_KEY = 0x5EED0001

from mecateca.config import get_settings
from mecateca.contexts.identity import service as identity_service
from mecateca.db import registry  # noqa: F401  (populate metadata)
from mecateca.db.engine import get_engine, get_sessionmaker
from mecateca.contexts.assessment.router import router as assessment_router
from mecateca.contexts.catalog.router import router as catalog_router
from mecateca.contexts.duels.router import router as duels_router
from mecateca.contexts.identity.router import router as identity_router
from mecateca.contexts.metering.router import router as metering_router
from mecateca.contexts.progression.router import router as progression_router
from mecateca.contexts.social.router import router as social_router
from mecateca.contexts.tutoring.router import router as tutoring_router
from mecateca.shared.errors import install_error_handlers
from mecateca.stubs import router as stubs_router

API = "/api/v1"


def _run_migrations() -> None:
    """Apply Alembic migrations (creates schema on a fresh DB, ALTERs an existing
    one). Never drops data. Runs in a worker thread so env.py's asyncio.run works."""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]  # backend/
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema is managed by migrations (idempotent; never resets) + bootstrap seed.
    # A session-level Postgres advisory lock serializes this across instances, so
    # two app replicas booting at once can't race the migration or double-seed.
    import asyncio
    async with get_engine().connect() as lock_conn:
        # A force-killed instance leaves a dead session holding the lock until the
        # server notices. Aggressive keepalives reap it in ~30s, and lock_timeout
        # makes a stuck boot fail loudly instead of hanging forever.
        await lock_conn.execute(text("SET tcp_keepalives_idle = 15"))
        await lock_conn.execute(text("SET tcp_keepalives_interval = 5"))
        await lock_conn.execute(text("SET tcp_keepalives_count = 3"))
        await lock_conn.execute(text("SET lock_timeout = '120s'"))
        await lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _STARTUP_LOCK_KEY})
        await lock_conn.execute(text("SET lock_timeout = 0"))
        try:
            await asyncio.to_thread(_run_migrations)
            async with get_sessionmaker()() as db:
                await identity_service.seed_admin(db)
                from mecateca.contexts.progression import tiers as tiers_mod
                await tiers_mod.seed_tiers(db, "standard")
                if get_settings().seed_demo:  # demo discipline — off for real deployments
                    from mecateca.contexts.catalog import seed_philosophy
                    await seed_philosophy.seed(db)  # idempotent: curriculum tests
                from mecateca.contexts.tutoring import service as tutor_service
                await tutor_service.purge_expired(db)  # hard-delete chats past the grace window
                await db.commit()
        finally:
            await lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _STARTUP_LOCK_KEY})
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="RankUp API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def security_mw(request: Request, call_next):
        # login rate-limiting moved into the /auth/login route (Postgres-backed,
        # shared across instances). This middleware only sets security headers.
        resp = await call_next(request)
        # SPA assets: always revalidate so edits show on a normal reload (dev-friendly)
        if request.method == "GET" and not request.url.path.startswith(API):
            resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        resp.headers["Content-Security-Policy"] = _CSP
        return resp

    @app.get("/healthz", tags=["meta"])
    async def healthz():
        return {"status": "ok", "llm": s.llm_label}

    for r in (
        identity_router,
        catalog_router,
        tutoring_router,
        assessment_router,
        progression_router,
        metering_router,
        social_router,
        duels_router,
        stubs_router,
    ):
        app.include_router(r, prefix=API)

    # rank logos: project-level "ranks simplified" folder (drop your own SVGs there). Mount before "/".
    ext_ranks = Path(__file__).resolve().parents[3] / "ranks simplified"
    if ext_ranks.is_dir():
        app.mount("/ranks", StaticFiles(directory=str(ext_ranks)), name="ranks")

    # serve the SPA (same origin -> no CORS). Mount last so API routes win.
    web = Path(__file__).resolve().parents[2] / "web"
    if web.is_dir():
        app.mount("/", StaticFiles(directory=str(web), html=True), name="web")

    return app


app = create_app()
