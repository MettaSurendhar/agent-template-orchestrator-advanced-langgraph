# src/api/routers

[#src-api-routers](#src-api-routers)

## What's here

| File | Endpoints | Purpose |
| --- | --- | --- |
| `auth.py` | `POST /auth/register`, `POST /auth/login` | Local account creation (creates/joins a team by name) and login |
| `runs.py` | `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` | Start/list/inspect/resume orchestration runs, scoped to the authenticated user's **team** |
| `reviews.py` | `GET /reviews/pending` | Team-wide view of every run currently paused for review |
| `audit.py` | `GET /audit` | The team's recent audit events |

## Conventions

- Every endpoint (except `auth.py`'s own) reads `request.state.team_id` for isolation — not `user_id`. `user_id` is still read where attribution matters (who started/resumed a run), but it never gates access.
- `runs.py`'s `_require_team_ownership(run_id, team_id)` gates `GET /runs/{id}` and `POST /runs/{id}/resume` — 404, not 403, for a run belonging to another team.
- `runs.py`'s `_sync_status_cache()` must be called after every state-changing operation (start, resume) — this keeps `reviews.py`'s queue accurate without it needing to touch the graph's live state at all.
- The compiled graph lives on `request.app.state.graph`, the Postgres pool on `request.app.state.pg_pool` — both set once in `app.py`'s lifespan handler.
- Raise `APIException` on failure; never let a raw exception escape.
