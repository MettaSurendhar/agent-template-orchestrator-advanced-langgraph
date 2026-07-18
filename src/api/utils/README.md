# src/api/utils

[#src-api-utils](#src-api-utils)

## What's here

- **`pg_util.py`** — every piece of app-level Postgres access: teams, users (local + SSO), run ownership + status cache, audit log. This is a **separate concern** from LangGraph's own checkpoint tables (managed entirely by `AsyncPostgresSaver` in `orchestrator/graph.py` + `app.py`) — even when both live in the same physical database, this module never touches the checkpointer's tables, and the checkpointer never touches these.

## Conventions

- **All app-level Postgres access goes through this file.** Don't write raw `psycopg` queries in a router — add a function here instead, following the existing pattern (`async def foo(pool, ...): async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur: ...`).
- `setup()` runs the full `CREATE TABLE IF NOT EXISTS` schema — idempotent, safe to call on every startup (which `app.py`'s lifespan does).
- The `orchestrator_runs` table's `status`/`pending_review_agent`/`pending_review_output` columns are a **denormalized cache**, not the source of truth (the graph's checkpointed state is) — see the module docstring and `CLAUDE.md`'s "review-queue status cache" section for why this exists and what keeps it in sync.
- Every row read that includes a `TIMESTAMPTZ` column returns a real Python `datetime` — callers (routers) are responsible for converting to `.isoformat()` before putting it in a Pydantic response model.
