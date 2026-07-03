# RankUp — Backend

FastAPI modular monolith serving the API **and** the SPA (`web/`). AI Socratic tutor,
ranked test marketplace, duels with Elo matchmaking, friends, progression ranks.
Fully subject-agnostic: disciplines are created in the admin panel or imported as YAML
packs. A Philosophy demo pack is seeded at boot (`MECATECA_SEED_DEMO=0` to disable).

See the [root README](../README.md) for the feature tour and architecture map.

## LLM backends

Pluggable via `MECATECA_LLM_BACKEND`:

| backend | what it is |
|---|---|
| `gateway` | any OpenAI-compatible endpoint (e.g. a local Claude Code API gateway) — default |
| `anthropic` | Anthropic API directly (`ANTHROPIC_API_KEY`) |
| `ollama` | local models (default `qwen3:4b`) |
| `fake` | deterministic, offline — used by the tests |

**Ollama on Windows:** if your user profile name has accents (e.g. `JoãoBento`),
`llama-server` fails to load models from `%USERPROFILE%\.ollama`. Set `OLLAMA_MODELS`
to an ASCII path (e.g. `C:\ollama\models`) and restart Ollama.

## Quick start

```bash
# 1. Postgres
docker compose up -d db

# 2. Install (src layout)
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env

# 3. Run — Alembic migrations + seed apply on startup (advisory-locked,
#    safe with multiple instances; never drops data)
uvicorn mecateca.main:app --port 8080
```

Open http://localhost:8080 (SPA) — API docs at `/docs`, health at `/healthz`.
Seeded admin login: `admin` / `admin` (dev only — change it).

## Tests & lint

```bash
pytest        # runs against the fake LLM provider + an isolated mecateca_test DB
ruff check src
```

CI (GitHub Actions) runs both on every push/PR with a Postgres 16 service.

## Migrations

Schema is managed by Alembic and applied automatically at boot. To add one:

```bash
alembic revision --autogenerate -m "what changed"
# review it — keep it additive/nullable + backfill so no data is ever lost
```

## Tools

- `python tools/shots.py [view ...]` — headless Playwright screenshots of the running app
  (defaults to all main views; `profile` is reached via the account rail)

## Layout

`src/mecateca/contexts/{identity,catalog,tutoring,assessment,progression,metering,social,duels}`
· `adapters/llm` · `web/` (vanilla JS SPA) · `alembic/` · `packs/`
