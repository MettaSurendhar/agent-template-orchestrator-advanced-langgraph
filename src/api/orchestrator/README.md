# src/api/orchestrator

[#src-api-orchestrator](#src-api-orchestrator)

This is the template's core — everything that makes it an *orchestrator* rather than a single-agent RAG loop lives here. The graph logic itself is unchanged from the POC and intermediate tiers; what's different at this tier is the checkpointer backing it and two new state fields.

## What's here

- **`state.py`** — `OrchestratorState`. Adds `team_id` (isolation scope) alongside `user_id` (attribution) — neither existed at the POC tier; the intermediate tier had `user_id` only.
- **`graph.py`** — `build_graph(checkpointer)`, unchanged signature from the intermediate tier. The checkpointer passed in is now `AsyncPostgresSaver` instead of `AsyncSqliteSaver` — the graph logic doesn't know or care which; that's the point of LangGraph's checkpointer interface being uniform.
- **`run_utils.py`** — `build_status_response()`, unchanged from earlier tiers.
- **`agents/`** — see its own README. The Supervisor, Summarizer, and 5 example specialists — **unchanged across all four tiers of this template family.**

## Conventions

- **Never mutate `OrchestratorState` in place** — every node returns a dict of the fields it's updating.
- `graph.py`'s `build_graph()` must be called exactly once per app process, inside the lifespan handler, with a checkpointer that's already open (see `app.py`).
- If you add a specialist, you only need to touch `agents/registry.py` — `graph.py` wires it in dynamically.
- The graph itself has no concept of "team" or "isolation" — that's entirely enforced at the router layer (`routers/runs.py`'s `_require_team_ownership()`). The graph just executes whatever `run_id`/`team_id`/`user_id` it's given in the initial state; keeping isolation logic out of the graph is deliberate, since the graph's job is orchestration, not access control.
