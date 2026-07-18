# CLAUDE.md

This is the **advanced tier (LangGraph)** of the Multi-Agent Orchestrator Template family. Read this before making changes.

## 0. This is one of two feature-equivalent advanced tiers

There's a sibling repo, **Advanced (AWS Strands)**, with the *same* feature set — Postgres durability, dual-mode auth, team isolation, review queue — built on AWS Strands Agents SDK instead of LangGraph. If a task is about the orchestration framework itself, that's a legitimate reason to be in one repo vs. the other. If a task is about a feature both should have, implement it here AND flag that the sibling repo needs the equivalent change — don't let them drift apart in capability, only in framework.

## What this is (and isn't)

The same dynamic Supervisor/specialist graph as the POC and intermediate tiers, now with: Postgres-backed durable state (survives restarts, handles concurrent writes properly), dual-mode auth (local JWT or Azure AD SSO), team-level isolation (any teammate can access a run, not just its starter), and a team-wide review queue.

**This is not** the repo to strip back down to SQLite or single-user assumptions — that regression belongs in the intermediate/POC tiers, which already exist for that purpose.

## Stack

| Concern | Choice |
|---|---|
| Framework | FastAPI + LangGraph |
| Orchestration | `StateGraph`, same shape as every other tier |
| State persistence | `AsyncPostgresSaver` — production-grade, verified against real Postgres |
| Auth | Local JWT (HS256) or Azure AD SSO (RS256 via JWKS) — dual-mode, same middleware |
| App-level persistence | `pg_util.py` — teams, users, run ownership + status cache, audit log, all async via `psycopg_pool` |
| Isolation scope | **Team**, not user — `request.state.team_id` gates every run-scoped endpoint |
| LLM | Bedrock by default at this tier (OpenAI still available via `LLM_PROVIDER=openai`) |

## Directory map

```
src/
├── app.py                             # FastAPI app; lifespan opens BOTH postgres resources
└── api/
    ├── __init__.py                    # Settings
    ├── client/llm_client.py            # generate_structured() — unchanged from earlier tiers
    ├── middleware/auth_middleware.py    # dual-mode JWT/SSO, attaches user_id + team_id
    ├── routers/
    │   ├── auth.py                     # register (creates/joins team by name), login
    │   ├── runs.py                     # team-scoped start/list/get/resume
    │   ├── reviews.py                  # GET /reviews/pending — team-wide review queue
    │   └── audit.py                    # GET /audit — team-scoped
    ├── schemas/{auth,runs,reviews,audit}.py
    ├── utils/pg_util.py                 # ALL app-level Postgres access goes through here
    ├── exceptions/custom_exceptions.py
    └── orchestrator/
        ├── state.py                    # OrchestratorState — now includes team_id + user_id
        ├── graph.py                    # build_graph(checkpointer) — unchanged signature from intermediate tier
        ├── run_utils.py
        └── agents/                     # unchanged from every earlier tier
```

## Two Postgres resources, opened once, in `app.py`'s lifespan

```python
async with (
    AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer,
    AsyncConnectionPool(settings.database_url, open=False) as pg_pool,
):
    await pg_pool.open()
    await checkpointer.setup()
    await pg_util.setup(pg_pool)
    ...
```

- `checkpointer` — LangGraph's own tables, holding graph execution state. Only ever touched via the compiled graph (`app.state.graph`). Never query these tables directly from a router.
- `pg_pool` — this app's own tables (teams/users/runs-cache/audit), all access through `pg_util.py`. Stored on `app.state.pg_pool`.

Both default to the same physical database (`DATABASE_URL`), on different table sets — no collision, but genuinely separate concerns in code. Set `CHECKPOINT_DATABASE_URL` if you want them physically separate.

**`checkpointer.setup()` and `pg_util.setup()` must both run before the graph is built or any request is served** — they create the tables if they don't exist. This only needs to happen once per deployment, but re-running it on every startup (as the lifespan handler does) is safe and cheap (`IF NOT EXISTS` everywhere).

## Team isolation, precisely

- A run's `team_id` is set once, at start, from `request.state.team_id` (itself resolved by the auth middleware from the user's row in `users`).
- `routers/runs.py`'s `_require_team_ownership()` gates `GET /runs/{id}` and `POST /runs/{id}/resume` — any user whose `team_id` matches the run's `team_id` passes, regardless of who started it.
- This is a deliberate, tested difference from the intermediate tier (which checks `user_id`, not `team_id`) — see `tests/test_api_e2e.py`'s `test_team_wide_visibility_and_cross_team_isolation_and_review_queue`, which registers two users on one team and one on another to prove both the "any teammate can access" and "other teams cannot" halves of this property.

## The review-queue status cache

`orchestrator_runs.status` / `pending_review_agent` / `pending_review_output` are denormalized copies of what the graph's live state already knows, updated by `routers/runs.py`'s `_sync_status_cache()` after every state-changing call (start, resume). `GET /reviews/pending` reads only from this cache — it never calls `graph.aget_state()` for every run in a team, which would be the naive approach and would get slow as a team accumulates run history. If you add a new state-changing endpoint, make sure it calls `_sync_status_cache()` too, or the queue will drift from reality.

## Conventions

- Every specialist agent is still built via `make_specialist_node()` in `agents/base.py` — unchanged across all four tiers.
- `AGENT_REGISTRY` in `registry.py` is still the only place you add/remove a specialist.
- All app-level Postgres access goes through `pg_util.py` — don't run raw `psycopg` queries in a router.
- Postgres returns `datetime` objects for `TIMESTAMPTZ` columns, not strings — every router that returns a timestamp field converts it explicitly (`.isoformat()`). This bit us once already while building this tier (a test caught it) — if you add a new endpoint returning a Postgres timestamp, don't forget this conversion.

## Testing this tier

`tests/test_graph_persistence.py` and `tests/test_api_e2e.py` both run against a **real Postgres instance**, not a mock — set `DATABASE_URL`/`CHECKPOINT_DATABASE_URL` (via `tests/conftest.py`, which points at a test database automatically) to a reachable Postgres before running `make test`. This tier's core value — durable state under real concurrent access, genuine team isolation — can't be honestly verified against an in-memory fake the way the POC tier's tests could.

## When to drop back a tier

If someone's evaluating this tier but doesn't actually need multi-team isolation or SSO, the intermediate tier (per-user isolation, SQLite, local JWT only) is meaningfully simpler to operate — point them there.

## Commands

```bash
make install
docker compose up -d postgres   # or point DATABASE_URL at an existing instance
make run
make test
```
