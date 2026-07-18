# Contributing

[#contributing](#contributing)

Before adding something, ask: *"Does the sibling AWS Strands repo need the equivalent change to stay feature-equivalent?"* If yes, flag it in your PR description even if you're not the one implementing it there.

Good contributions: bug fixes, improvements to the status-cache sync logic, a new audit event type, better SSO error messages, additional test coverage for team-isolation edge cases.

Belongs in a different tier instead: anything that would remove Postgres/SSO/team-isolation to "simplify" this tier — that's what the intermediate/POC tiers are for.

## Setup

```bash
docker compose up -d postgres
make install
```

## Making a change

1. Branch from `main`.
2. If touching `pg_util.py`, `app.py`'s lifespan, or team-isolation logic in `routers/runs.py`, run the full test suite against real Postgres — these are exactly the areas where a mock would hide a real bug (see `CLAUDE.md`'s note on the datetime-serialization bug the test suite caught during development).
3. Run `make test` before opening a PR. Postgres must be running.

## Reporting bugs

Include whether the issue is in team isolation (wrong user seeing/not-seeing a run), the review queue (stale or missing entries), or SSO (token verification failures) — these point at different parts of the codebase.
