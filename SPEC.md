# MecaTeca — Backend Spec (v1)

Python webservice. Built so new **subjects** and new **features** drop in without rewrites.
v1 ships **Philosophy** only, with **AI Socratic tutor (text)** + **practice tests / ranked ladder**.
Voice, evaluation booking and credentials are designed-for but not built in v1.

---

## 0. Decisions (locked)

| Area | Choice | Why |
|---|---|---|
| Web | **FastAPI** (async) | Streaming (SSE/WS), Pydantic typing, fits AI + future voice |
| v1 modules | Socratic tutor (text), Practice/Ranked ladder | Core learning loop first |
| Voice | Text-first; voice later behind a port | Avoid realtime infra at start |
| Persistence | **PostgreSQL only** | Mastery graph as closure-table + JSONB; transactional |

### Defaults I assumed (flip any — see §13)
Python 3.12 · `uv` · SQLAlchemy 2.0 async + asyncpg + Alembic · Pydantic v2 + pydantic-settings ·
Anthropic SDK (async) · Redis (cache / quota / rate-limit; ARQ for jobs later) ·
Auth = own JWT (access+refresh, argon2) + RBAC · Docker · structlog + OTel + Sentry · pytest + httpx + testcontainers.

---

## 1. Architecture — modular monolith, hexagonal

One deployable, split into **bounded contexts** with a strict dependency rule:

```
            ┌──────────────────────── interfaces (FastAPI routers, SSE) ───────────────────────┐
            │                              depends on ↓                                          │
            │     application services (use-cases, orchestration, transactions)                  │
            │                              depends on ↓                                          │
            │     domain (entities, value objects, events, ports/Protocols) — NO I/O             │
            │                              ↑ implemented by                                       │
            │     adapters (SQLAlchemy repos, Anthropic provider, Redis, clock, ids)             │
            └────────────────────────────────────────────────────────────────────────────────────┘
```

Rule: domain imports nothing outward. Adapters implement domain `Protocol` ports. Services wire them.
This is what lets us swap Claude→another LLM, Postgres→graph DB, or extract a context into its own service later — without touching domain logic.

### Bounded contexts (v1 = ✅, designed = 🔜)
- ✅ `identity` — users, auth, roles, sessions
- ✅ `catalog` — subjects, **Mastery Graph** (concepts + edges), question templates, rubrics
- ✅ `tutoring` — Socratic chat activity
- ✅ `assessment` — practice tests, answers, grading
- ✅ `progression` — XP/ranks/streaks/seasons (event-sourced), leaderboards
- ✅ `metering` — usage + plan quotas (ties to billing model)
- 🔜 `evaluation` — human 1-on-1 booking + sessions
- 🔜 `credentials` — verifiable credential issuance + public verify
- 🔜 `voice` — STT/TTS realtime port

---

## 2. The three extensibility seams (the "future-proof" core)

Everything new is one of three plugin shapes. New work = implement an interface + register it; no edits to existing contexts.

### 2.1 Subject Packs — new subject matter, **no deploy**
A subject is **data**, not code. A versioned pack is authored as YAML, validated, imported into Postgres. Adding "Mathematics" or "History" = import a pack.

`packs/philosophy/1.0.0/pack.yaml` (excerpt, pt-PT):
```yaml
subject:
  key: philosophy
  name: Filosofia
  version: 1.0.0
  locale: pt-PT
  progression_profile: standard      # references a ProgressionProfile (ranks/xp rules)
concepts:                            # Mastery Graph nodes
  - key: epistemologia.cvj
    name: Crença verdadeira justificada
    summary: A análise tripartida do conhecimento.
    difficulty: 2
    prerequisites: [epistemologia.crenca-vs-conhecimento]
    objectives:
      - Distinguir crença de conhecimento
      - Explicar as três condições da CVJ
    misconceptions:
      - id: cvj-ignora-gettier
        text: Assumir que CVJ é suficiente para conhecimento.
    tutor:
      strategy: socratic
      seed_questions:                # nudges, never answers
        - "O que falta a uma crença verdadeira para ser conhecimento?"
question_templates:
  - key: cvj-mcq-1
    concept: epistemologia.cvj
    kind: mcq                        # mcq | short | reasoning
    difficulty: 2
    source: static                   # static bank OR ai-generated
    payload: { stem: "...", options: ["..."], answer_index: 1, why: "..." }
  - key: cvj-reasoning-1
    concept: epistemologia.cvj
    kind: reasoning
    difficulty: 3
    source: ai
    rubric: reasoning-default
rubrics:
  - key: reasoning-default
    criteria:
      - { key: understanding, weight: 0.4, descriptor: "Identifica o conceito central" }
      - { key: reasoning,     weight: 0.4, descriptor: "Justifica com raciocínio próprio" }
      - { key: application,   weight: 0.2, descriptor: "Aplica a um caso novo" }
```
Pack schema is itself versioned (`pack_schema_version`). Importer = pure validation (Pydantic models) → upsert into `concept`, `concept_edge`, `question_template`, `rubric` under a `subject_version`. Old versions stay (reproducibility). See §5.

### 2.2 Activity plugins — new feature / learning surface
Every interactive surface (tutor chat, practice test, future: voice eval, debate mode) implements one interface and is registered by `type`.
```python
# domain/activities/base.py
from typing import Protocol, AsyncIterator

class Activity(Protocol):
    type: str  # "socratic_chat", "practice_test", ...

    async def start(self, ctx: "ActivityContext", params: dict) -> "ActivityState": ...
    async def step(self, ctx: "ActivityContext", state: "ActivityState",
                   user_input: "ActivityInput") -> AsyncIterator["DomainEvent"]: ...
```
- `tutoring.SocraticChatActivity` and `assessment.PracticeTestActivity` ship in v1.
- A new feature = new `Activity`; the router + progression react to the **events** it emits, so nothing else changes.

### 2.3 Strategy ports — swap implementations
```python
class LLMProvider(Protocol):
    async def stream(self, req: LLMRequest) -> AsyncIterator[str]: ...
    async def parse(self, req: LLMRequest, schema: type[T]) -> T: ...   # structured output

class Grader(Protocol):
    kind: str  # "mcq", "ai_reasoning", "human"
    async def grade(self, answer: Answer, question: Question, rubric: Rubric | None) -> Grade: ...

class MasteryModel(Protocol):
    def update(self, prior: float, outcome: GradeOutcome, difficulty: int) -> float: ...
```
v1 impls: `AnthropicProvider`, `MCQGrader` + `AIReasoningGrader`, `DecayBKTMastery`.
Future `HumanGrader` (evaluation context) plugs into the same `Grader` port.

---

## 3. Project layout

```
mecateca/
  pyproject.toml            # uv-managed
  alembic/                  # migrations
  packs/                    # subject packs (versioned)
    philosophy/1.0.0/pack.yaml
  src/mecateca/
    main.py                 # FastAPI app factory, lifespan, router include
    config.py               # pydantic-settings (env)
    deps.py                 # DI providers (db session, current_user, ratelimit)
    db/
      base.py engine.py session.py
    shared/
      events.py             # DomainEvent base + bus
      ids.py clock.py errors.py pagination.py
    contexts/
      identity/    {router.py service.py models.py schemas.py security.py}
      catalog/     {router.py service.py models.py schemas.py pack_loader.py graph.py}
      tutoring/    {router.py service.py activity.py prompts.py models.py schemas.py}
      assessment/  {router.py service.py activity.py graders.py models.py schemas.py}
      progression/ {router.py service.py rules.py projector.py models.py schemas.py}
      metering/    {service.py models.py quota.py}
    adapters/
      llm/anthropic_provider.py  llm/router.py  llm/base.py
      cache/redis.py
  tests/
    conftest.py  (testcontainers PG, async client, factories)
    contexts/...  e2e/...
```

---

## 4. Tech stack (pinned)

```toml
# pyproject.toml (core)
dependencies = [
  "fastapi>=0.115", "uvicorn[standard]>=0.32",
  "pydantic>=2.9", "pydantic-settings>=2.6",
  "sqlalchemy[asyncio]>=2.0", "asyncpg>=0.30", "alembic>=1.14",
  "anthropic>=0.69",          # async client; pin to current
  "redis>=5.2",
  "pyjwt>=2.10", "argon2-cffi>=23.1",
  "structlog>=24.4", "sentry-sdk>=2.18",
  "pyyaml>=6.0",
]
# dev: ruff, mypy, pytest, pytest-asyncio, httpx, testcontainers[postgres], polyfactory
```

---

## 5. Data model (PostgreSQL)

Conventions: UUIDv7 PKs (`ids.new_id()`), `created_at/updated_at` timestamptz, soft-delete only where needed, JSONB for plugin-shaped payloads. All money/cost in integer micro-EUR.

### identity
```sql
user( id pk, email citext unique, password_hash text, role text check(role in('student','teacher','admin')),
      display_name text, locale text default 'pt-PT', plan text default 'free', created_at, updated_at )
refresh_token( id pk, user_id fk, token_hash text, expires_at, revoked_at )
```

### catalog (Mastery Graph)
```sql
subject( id pk, key text unique, name text, current_version_id fk null )
subject_version( id pk, subject_id fk, version text, pack_schema_version text, locale text,
                 progression_profile text, imported_at, UNIQUE(subject_id, version) )

concept( id pk, subject_version_id fk, key text, name text, summary text, difficulty int,
         objectives jsonb, misconceptions jsonb, tutor jsonb, UNIQUE(subject_version_id, key) )
-- edges = prerequisite DAG. Direct edges + closure table for O(1) reachability.
concept_edge( subject_version_id fk, parent_concept_id fk, child_concept_id fk, kind text default 'prerequisite',
              PRIMARY KEY(parent_concept_id, child_concept_id) )
concept_closure( ancestor_id fk, descendant_id fk, depth int, PRIMARY KEY(ancestor_id, descendant_id) )

question_template( id pk, subject_version_id fk, key text, concept_id fk, kind text, difficulty int,
                   source text, payload jsonb, rubric_id fk null )
rubric( id pk, subject_version_id fk, key text, criteria jsonb )
```
Graph queries: prerequisites/unlocks via `concept_closure` (rebuilt on import) or recursive CTE for ad-hoc. Closure table keeps "is X ready?" cheap at scale.

### tutoring
```sql
tutor_session( id pk, user_id fk, subject_version_id fk, concept_id fk null, status text, created_at )
tutor_message( id pk, session_id fk, role text check(role in('user','assistant')),
               content text, tokens_in int, tokens_out int, model text, created_at )
```

### assessment
```sql
practice_session( id pk, user_id fk, subject_version_id fk, focus_concept_id fk null,
                  difficulty int, status text, created_at )
practice_item( id pk, session_id fk, concept_id fk, question_template_id fk null,
               kind text, payload jsonb, ordinal int )           -- payload = generated/static question
answer( id pk, item_id fk unique, user_id fk, raw jsonb, submitted_at,
        grade jsonb, reasoning_score numeric, correct bool, graded_by text )  -- idempotent on item_id
```

### progression (event-sourced)
```sql
progression_event( id pk, user_id fk, subject_id fk, season_id fk null, type text, payload jsonb,
                   created_at, seq bigint )                       -- append-only, the source of truth
-- materialized projections (rebuildable from events):
user_subject_progress( user_id fk, subject_id fk, season_id fk, xp int, rank text, streak int,
                       updated_at, PRIMARY KEY(user_id, subject_id, season_id) )
user_concept_mastery( user_id fk, concept_id fk, mastery numeric, last_seen_at,
                      PRIMARY KEY(user_id, concept_id) )          -- drives adaptivity / spaced repetition
season( id pk, subject_id fk null, key text, starts_at, ends_at )
```

### metering
```sql
usage_event( id pk, user_id fk, kind text, model text, tokens_in int, tokens_out int,
             cost_micro_eur bigint, ref_id uuid, created_at )
```

---

## 6. Progression engine (config, not code)

Ranks, thresholds and XP rules live in a **ProgressionProfile** (YAML/DB), referenced by a subject. Changing scoring ≠ code change.
```yaml
# progression/profiles/standard.yaml
key: standard
ranks: [ {name: Bronze, xp: 0}, {name: Silver, xp: 120}, {name: Gold, xp: 300}, {name: Diamond, xp: 560} ]
xp_rules:
  correct_base: 40
  streak_bonus_per: 5            # +5 * streak
  reasoning_multiplier: 1.0      # XP scales with reasoning_score (anti-offload core)
  wrong: 0
```
Flow: an `Activity` emits domain events (`AnswerGraded{correct, reasoning_score, difficulty}`) → `progression.projector` applies `xp_rules` → appends `XpAwarded` / `RankUp` to `progression_event` → updates `user_subject_progress`. Rebuild any projection by replaying events (audit-friendly — matters because trust is the product).

**Anti-offload baked in:** XP scales with `reasoning_score` from the grader, not just correctness. New scoring schemes = new profile, hot-swappable per subject/season.

---

## 7. AI integration (Anthropic Claude)

### Model routing (cost-aware)
```python
# adapters/llm/router.py
ROUTING = {
  "tutor_socratic": "claude-haiku-4-5",     # cheap, high-volume
  "grade_reasoning": "claude-haiku-4-5",    # structured output, cheap
  "generate_question": "claude-sonnet-4-6", # quality matters
  # voice / deep reasoning later -> sonnet/opus
}
```
- **Streaming** tutor replies over SSE using `client.messages.stream(...)`.
- **Structured outputs** for grading via `messages.parse(... output_config={"format": ...})` → typed `Grade` (no fragile parsing).
- **Prompt caching**: subject system prompt + concept context carry `cache_control:{type:"ephemeral"}` so the stable prefix is ~0.1× cost across a session. Keep volatile bits (the student's message) after the breakpoint.
- **Adaptive thinking** off for tutor (latency), considered for grading hard reasoning.
- **Token metering**: every call records `usage_event` (tokens + micro-EUR via a price table); `metering.quota` blocks free-tier users past caps before the call.

### Socratic prompt assembly
System prompt = role ("orienta, nunca dá a resposta") + concept objectives + misconceptions + `seed_questions`, all from the pack. Provider is a port, so swapping models/providers is config-only.

```python
class AnthropicProvider(LLMProvider):
    def __init__(self, client: AsyncAnthropic, router, prices): ...
    async def stream(self, req): 
        async with self._client.messages.stream(model=self._router[req.task], max_tokens=1024,
            system=req.system_blocks, messages=req.messages) as s:   # system_blocks carry cache_control
            async for text in s.text_stream: yield text
        await self._meter(req, await s.get_final_message())
    async def parse(self, req, schema):
        return (await self._client.messages.parse(model=self._router[req.task], max_tokens=1024,
            messages=req.messages, output_config={"format": pydantic_format(schema)})).parsed_output
```

---

## 8. API surface (v1, `/api/v1`)

REST + JSON. Tutor streaming via SSE. Cursor pagination. Idempotency-Key header on writes that must not double-apply (answer submit).

```
# identity
POST /auth/register            {email,password,display_name}
POST /auth/login               -> {access, refresh}
POST /auth/refresh
GET  /me

# catalog
GET  /subjects
GET  /subjects/{key}                          # current version meta
GET  /subjects/{key}/graph                    # concepts + edges (Mastery Graph)
GET  /concepts/{id}

# tutoring (SSE)
POST /tutor/sessions                          {subject, concept?}
POST /tutor/sessions/{id}/messages            {text}  -> text/event-stream (token deltas + done event)
GET  /tutor/sessions/{id}

# assessment
POST /practice/sessions                       {subject, concept?, difficulty}  -> session + items
GET  /practice/sessions/{id}
POST /practice/items/{id}/answer              {raw}  (Idempotency-Key) -> grade + xp delta + rank

# progression
GET  /me/progress/{subject}                   # xp, rank, streak, weak concepts
GET  /leaderboards/{subject}?season=current

# metering
GET  /me/usage                                # tokens + remaining free quota

# admin / content
POST /admin/subjects/import                   # upload pack.yaml -> validate -> new subject_version
POST /admin/subjects/{key}/activate           {version}
```
Stubbed routers (return 501, interfaces defined) for 🔜 `evaluation`, `credentials`.

---

## 9. AuthN / AuthZ

- JWT access (~15 min) + rotating refresh (hashed, stored). argon2id hashing.
- RBAC dependency: `require_role("admin")`, `current_user`. v1 roles: student, admin (teacher arrives with `evaluation`).
- Per-route + per-user rate limits in Redis. Ownership checks in services (a user only reads own sessions).
- Pluggable to OAuth/Clerk later — auth is a `deps.current_user` provider, swap without touching routers.

---

## 10. Non-functional

- **Config**: `pydantic-settings`, `.env`; secrets via env/secret-manager; price table for cost calc in config.
- **Migrations**: Alembic, autogenerate gated by review; closure-table rebuild in import service, not migration.
- **Testing**: pytest-asyncio; `testcontainers[postgres]` for real PG; httpx `AsyncClient`; polyfactory fixtures; LLM provider faked via the port (deterministic). Pack-loader has golden-file tests.
- **Observability**: structlog JSON, request-id middleware, OpenTelemetry traces (DB + LLM spans), Sentry. LLM spans tag model + tokens + cost.
- **Cost control**: model routing, prompt caching, structured-output grading, `max_tokens` caps, per-user quota enforcement, Batch API for any non-realtime bulk (not tutor).
- **i18n**: content is locale-tagged per subject version (`pt-PT` first); API returns locale from user.
- **Security**: input validation (Pydantic), output encoding, SQLi-safe (ORM params), rate limits, no secrets in prompts/logs, CORS allowlist.
- **Deploy**: Docker image (uvicorn workers); 12-factor; healthcheck `/healthz`; readiness checks DB+Redis.

---

## 11. How each future feature slots in (no rewrite)

| Future feature | Seam used | What you add |
|---|---|---|
| New subject (Math, History) | Subject Pack | author + import a pack; zero deploy |
| Voice-to-voice tutor | Activity + new `voice` port | `VoiceChatActivity` over WebSocket; STT/TTS adapters; reuses tutoring prompts |
| Human evaluation booking | new `evaluation` context | scheduling tables + `HumanGrader` (same `Grader` port) emitting same events |
| Verifiable credential | new `credentials` context | listens for `EvaluationPassed` event → signs credential; public verify endpoint |
| New scoring / seasons | ProgressionProfile | new profile YAML; replay events if backfilling |
| Swap/aug LLM | `LLMProvider` | new adapter + routing entry |
| Featured/marketplace, etc. | new context | append-only events keep history intact |

The flat per-evaluation fee + Pro metering both already have homes (`metering`, future `evaluation`).

---

## 12. Build order (v1)

1. Skeleton: app factory, config, DB session, Alembic, identity (auth + RBAC), `/healthz`.
2. catalog: pack schema (Pydantic) + loader + Philosophy pack + graph endpoints + closure build.
3. metering: usage_event + quota + price table (wire into a fake provider first).
4. tutoring: SocraticChatActivity + AnthropicProvider (stream) + SSE endpoint + prompt assembly from pack.
5. assessment: PracticeTestActivity + MCQ/AIReasoning graders + answer endpoint (idempotent).
6. progression: events + projector + ProgressionProfile + progress/leaderboard endpoints.
7. Hardening: tests (testcontainers), observability, rate limits, Docker, CI.

---

## 13. Open decisions to confirm

1. **ORM**: SQLAlchemy 2.0 async (my pick) vs SQLModel (less boilerplate, some sharp edges).
2. **Auth build**: hand-rolled JWT (my pick, full control) vs `fastapi-users` (faster, opinionated).
3. **Pack format**: YAML (my pick, human-authorable) vs JSON vs DB-admin UI later.
4. **Question generation in v1**: static bank only, or allow AI-generated items from `source: ai` from day one (cost + caching implications).
5. **Mastery model**: simple decay+correctness (my pick for v1) vs BKT/Elo now.
6. **Multi-tenant?** Single-tenant assumed (one MecaTeca). Confirm no white-label need yet.
7. **Jobs**: none needed in v1 (all request-scoped). Add ARQ+Redis when voice/booking arrive — confirm.
```
