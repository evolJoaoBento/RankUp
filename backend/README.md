# MecaTeca — Backend (v1)

FastAPI modular monolith. AI Socratic tutor (text) + practice tests / ranked ladder.
Ships **Philosophy**. New subjects = import a YAML pack (no deploy). See `../spec.html`.

LLM backend is pluggable (`MECATECA_LLM_BACKEND`): **`ollama`** (local, default — `qwen3:4b`),
`anthropic`, or `fake` (deterministic, offline, used by the tests).

### Local AI (Ollama)
```bash
# install ollama (https://ollama.com), then:
ollama pull qwen3:4b         # default — fits 8GB GPUs; needs Ollama >= 0.5 for structured grading
# bigger GPU? ollama pull qwen3:8b  and set MECATECA_OLLAMA_MODEL=qwen3:8b
```
**Windows note:** if your user profile name has accents (e.g. `JoãoBento`), `llama-server`
fails to load models from `%USERPROFILE%\.ollama`. Set `OLLAMA_MODELS` to an ASCII path
(e.g. `C:\ollama\models`) and restart Ollama.
qwen3's "thinking" output is auto-disabled (`MECATECA_OLLAMA_THINK=auto`) so tutor text and
grading JSON stay clean.

## Quick start

```bash
# 1. Postgres
docker compose up -d db

# 2. Install (src layout)
python -m venv .venv && . .venv/bin/activate     # (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"
cp .env.example .env

# 3. Create schema + load the Philosophy pack + a demo season
mecateca initdb
mecateca loadpack packs/philosophy/1.0.0/pack.yaml

# 4. Run
uvicorn mecateca.main:app --reload
# docs at http://localhost:8000/docs
```

## Smoke test (curl)

```bash
# register + login
curl -s localhost:8000/api/v1/auth/register -H 'content-type: application/json' \
  -d '{"email":"a@b.c","password":"pw12345678","display_name":"Ana"}'
TOKEN=$(curl -s localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"a@b.c","password":"pw12345678"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access"])')

# subject graph
curl -s localhost:8000/api/v1/subjects/philosophy/graph -H "authorization: Bearer $TOKEN"

# start a practice session, answer an item
SID=$(curl -s localhost:8000/api/v1/practice/sessions -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"subject":"philosophy","difficulty":2}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')
```

## Layout
`src/mecateca/contexts/{identity,catalog,tutoring,assessment,progression,metering}` ·
`adapters/llm` · `packs/` · `db/` · `shared/`.

## Migrations
`mecateca initdb` (create_all) is for dev. For prod use Alembic:
`alembic revision --autogenerate -m "x"` then `alembic upgrade head`.
