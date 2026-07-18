# src/api/schemas

[#src-api-schemas](#src-api-schemas)

## What's here

- `auth.py` — `RegisterRequest` (now includes `team_name`), `LoginRequest`, `AuthResponse` (now includes `team_id`).
- `runs.py` — `StartRunRequest`, `RunStatusResponse`, `PendingReview`, `ResumeRequest`, `RunSummary` (now includes `started_by_user_id` and `status`), `RunListResponse`.
- `reviews.py` — `PendingReviewItem`, `PendingReviewListResponse`.
- `audit.py` — `AuditEvent` (now includes `team_id`), `AuditLogResponse`.

## Conventions

- Any field sourced from a Postgres `TIMESTAMPTZ` column must be a `str` in the schema, with the router converting the `datetime` object via `.isoformat()` before constructing the response model — Postgres returns real `datetime` objects, not strings, and Pydantic will reject them otherwise (this bit the development of this tier once; see `CLAUDE.md`).
- `RunSummary` includes `started_by_user_id` specifically so a team's run list can show attribution even though access isn't restricted to that user.
