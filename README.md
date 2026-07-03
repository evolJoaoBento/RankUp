# RankUp

[![CI](https://github.com/evolJoaoBento/RankUp/actions/workflows/ci.yml/badge.svg)](https://github.com/evolJoaoBento/RankUp/actions/workflows/ci.yml)

**Aprende a sério. Ranks que se conquistam.**

RankUp is a gamified learning platform for schools. Students study with an AI Socratic tutor, take ranked tests from a marketplace, duel friends in real-time question battles, and climb a Valorant-style rank ladder — from **Wood** to **Ascended** — by earning EP for *reasoning*, not just right answers.

![Tutor](docs/screenshots/tutor.png)

## Features

### 🧠 Socratic AI Tutor
A chat tutor that never gives the answer — it guides the student towards it. Conversations are grounded in teacher-approved study materials, saved per subject, renamable in place, and recoverable for 6 months after deletion. Empty chats offer quick-start prompts.

### 🏆 Ranked test marketplace
Teachers (or the AI) create tests; students take them and earn EP for their reasoning. Tests are linked to the materials that ground them, searchable, and show who submitted and who approved each one. Test runs have a live progress bar and completion summary; every subject has an EP ladder that always shows your own position. Flashcard decks flip on click (or spacebar) with full keyboard navigation.

![Ranked](docs/screenshots/practice.png)

### ⚔️ Duels
Two players pick one material each from the same discipline and take turns authoring questions (2 min) that both answer simultaneously (3 min). An AI judge picks the most correct answer each round — win 2 pts, draw 1 pt each. Includes:

- **Ranked matchmaking** with Elo rating (K=32, chess-style) and a widening search window
- **Friend duels** — challenge anyone on your friends list, rematch in one click
- Coin-flip first turn, forfeit at any time, live leaderboard
- "Your turn" highlights and a red action counter on the nav

![Duels](docs/screenshots/duels.png)

### 📚 Materials
Study references that feed the tutor and ground the tests. Students can submit materials; teachers and admins approve them. Every material shows its author and approver.

![Materials](docs/screenshots/materials.png)

### 📈 Progression & profile
Per-subject EP, rank badges with unlockable background colours, streaks, weak-topic detection, duel history and Elo record.

![Profile](docs/screenshots/profile.png)

### 🛠 Admin panel
Tabbed admin area with a platform-overview dashboard (accounts, pending materials, duels, …) and searchable table editors for accounts, disciplines (with SVG icon picker) and conversations (including soft-deleted chat recovery), plus AI usage metering per user.

![Admin](docs/screenshots/admin.png)

## Architecture

```
backend/
├── src/mecateca/
│   ├── contexts/          # bounded contexts (modular monolith)
│   │   ├── identity/      # auth (JWT), roles, login throttling
│   │   ├── catalog/       # subjects, materials, tests, approval flow
│   │   ├── tutoring/      # Socratic chat (SSE streaming, soft delete)
│   │   ├── assessment/    # practice sessions, AI grading
│   │   ├── progression/   # EP, ranks, streaks, leaderboards
│   │   ├── metering/      # token usage + cost quotas
│   │   ├── social/        # friends
│   │   └── duels/         # duel state machine, Elo, matchmaking, AI judge
│   ├── adapters/llm/      # pluggable LLM providers
│   └── main.py            # FastAPI app + advisory-locked startup migrations
├── web/                   # vanilla JS SPA (no build step)
├── alembic/               # migrations (additive, data-preserving)
└── packs/                 # subject content packs (YAML)
```

- **Stack:** FastAPI · SQLAlchemy 2 (async) · PostgreSQL 16 · Alembic · vanilla JS SPA
- **LLM backends** (`MECATECA_LLM_BACKEND`): `gateway` (OpenAI-compatible, e.g. a Claude Code gateway), `anthropic`, `ollama` (local), or `fake` (deterministic, for tests)
- Multi-instance safe: startup migrations serialized with a Postgres advisory lock; DB-backed login rate limiting; atomic row-claims prevent double-judging duels

## Quick start

```bash
cd backend

# 1. Postgres
docker compose up -d db

# 2. Install
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env

# 3. Run (migrations + seed run on startup)
uvicorn mecateca.main:app --port 8080
```

Open http://localhost:8080 — the SPA is served by the backend. API docs at `/docs`.

Default LLM backend is `ollama`; set `MECATECA_LLM_BACKEND=gateway` and `MECATECA_GATEWAY_BASE_URL` to use an OpenAI-compatible gateway instead.

## Development

- `backend/tools/shots.py` — headless Playwright screenshots of every view (`python tools/shots.py`)
- `pytest` — runs against the `fake` LLM provider, no network needed
- Migrations: `alembic revision --autogenerate -m "..."` then restart the app (they apply on boot)
