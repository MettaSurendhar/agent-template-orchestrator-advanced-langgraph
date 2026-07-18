"""Postgres-backed persistence for teams, users, run ownership/status cache, and the
audit log.

This is a SEPARATE concern from LangGraph's own checkpoint tables (holding actual graph
execution state, managed entirely by `AsyncPostgresSaver`) — even though both may live in
the same physical database (see `settings.database_url` vs `checkpoint_database_url`),
this module only ever touches its own tables (`teams`, `users`, `orchestrator_runs`,
`audit_log`), never the checkpointer's.

`orchestrator_runs` intentionally caches `status` and pending-review info, updated by
`routers/runs.py` after every state-changing call. This is a deliberate denormalization:
without it, the review queue (`GET /reviews/pending`) would need to call `graph.aget_state()`
for every run a team has ever started just to find the paused ones — fine for a handful of
runs, expensive at real team scale. The cache trades a small update-time cost for a cheap
read on the endpoint that matters most for a team lead using this daily.
"""

import json
import uuid
from datetime import datetime, timezone

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

_SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    team_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    salt TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS orchestrator_runs (
    run_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    started_by_user_id TEXT NOT NULL,
    user_request TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    pending_review_agent TEXT,
    pending_review_output JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    team_id TEXT,
    user_id TEXT,
    run_id TEXT,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL
);
"""


async def setup(pool: AsyncConnectionPool) -> None:
    """Create the app's own tables if they don't exist. Called once at startup."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(_SCHEMA)


# --- Teams ---


async def get_or_create_team(pool: AsyncConnectionPool, team_name: str) -> str:
    """Return the team_id for `team_name`, creating the team if it doesn't exist yet."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT team_id FROM teams WHERE team_name = %s", (team_name,))
        row = await cur.fetchone()
        if row:
            return row["team_id"]

        team_id = f"team-{uuid.uuid4().hex[:12]}"
        await cur.execute(
            "INSERT INTO teams (team_id, team_name, created_at) VALUES (%s, %s, %s)",
            (team_id, team_name, datetime.now(timezone.utc)),
        )
        return team_id


async def ensure_default_team(pool: AsyncConnectionPool, team_id: str, team_name: str) -> None:
    """Idempotently ensure a specific team_id/name exists — used for DEFAULT_TEAM_ID at startup."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO teams (team_id, team_name, created_at) VALUES (%s, %s, %s) ON CONFLICT (team_id) DO NOTHING",
            (team_id, team_name, datetime.now(timezone.utc)),
        )


# --- Users ---


async def create_local_user(pool: AsyncConnectionPool, email: str, password_hash: str, salt: str, team_id: str) -> str:
    """Create a new locally-authenticated user, returning the new user_id."""
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO users (user_id, email, password_hash, salt, auth_provider, team_id, created_at) "
            "VALUES (%s, %s, %s, %s, 'local', %s, %s)",
            (user_id, email, password_hash, salt, team_id, datetime.now(timezone.utc)),
        )
    return user_id


async def get_or_create_sso_user(pool: AsyncConnectionPool, email: str, default_team_id: str) -> dict:
    """Look up an SSO user by email, auto-onboarding into `default_team_id` on first login."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = await cur.fetchone()
        if row:
            return dict(row)

        user_id = f"user-{uuid.uuid4().hex[:12]}"
        await cur.execute(
            "INSERT INTO users (user_id, email, auth_provider, team_id, created_at) VALUES (%s, %s, 'azure_ad', %s, %s)",
            (user_id, email, default_team_id, datetime.now(timezone.utc)),
        )
        return {"user_id": user_id, "email": email, "auth_provider": "azure_ad", "team_id": default_team_id}


async def get_user_by_email(pool: AsyncConnectionPool, email: str) -> dict | None:
    """Fetch a user by email."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_by_id(pool: AsyncConnectionPool, user_id: str) -> dict | None:
    """Fetch a user by user_id — used by the auth middleware to resolve the current team."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


# --- Run ownership + status cache ---


async def register_run(pool: AsyncConnectionPool, run_id: str, team_id: str, user_id: str, user_request: str) -> None:
    """Record a newly-started run, owned by the team."""
    now = datetime.now(timezone.utc)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO orchestrator_runs "
            "(run_id, team_id, started_by_user_id, user_request, status, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, 'running', %s, %s)",
            (run_id, team_id, user_id, user_request, now, now),
        )


async def update_run_status(
    pool: AsyncConnectionPool, run_id: str, status: str, pending_agent: str | None, pending_output: dict | None
) -> None:
    """Update the cached status/pending-review fields for a run — call after every state-changing operation."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "UPDATE orchestrator_runs SET status = %s, pending_review_agent = %s, pending_review_output = %s, "
            "updated_at = %s WHERE run_id = %s",
            (status, pending_agent, json.dumps(pending_output) if pending_output else None, datetime.now(timezone.utc), run_id),
        )


async def get_run_team(pool: AsyncConnectionPool, run_id: str) -> str | None:
    """Return the team_id that owns a run, or None if the run is unknown."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT team_id FROM orchestrator_runs WHERE run_id = %s", (run_id,))
        row = await cur.fetchone()
        return row["team_id"] if row else None


async def list_team_runs(pool: AsyncConnectionPool, team_id: str) -> list[dict]:
    """List all of a team's runs, most recent first."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM orchestrator_runs WHERE team_id = %s ORDER BY created_at DESC", (team_id,)
        )
        return [dict(row) for row in await cur.fetchall()]


async def list_pending_reviews(pool: AsyncConnectionPool, team_id: str) -> list[dict]:
    """List every run in the team currently paused for review — the review queue's data source."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM orchestrator_runs WHERE team_id = %s AND status = 'paused' ORDER BY updated_at ASC",
            (team_id,),
        )
        return [dict(row) for row in await cur.fetchall()]


# --- Audit log ---


async def log_event(
    pool: AsyncConnectionPool,
    team_id: str | None,
    user_id: str | None,
    run_id: str | None,
    event_type: str,
    description: str,
    metadata: dict | None = None,
) -> None:
    """Record an audit event."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO audit_log (id, team_id, user_id, run_id, event_type, description, metadata, timestamp) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                f"audit-{uuid.uuid4().hex[:12]}",
                team_id,
                user_id,
                run_id,
                event_type,
                description,
                json.dumps(metadata or {}),
                datetime.now(timezone.utc),
            ),
        )


async def get_audit_log(pool: AsyncConnectionPool, team_id: str, limit: int = 100) -> list[dict]:
    """Fetch a team's recent audit events."""
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM audit_log WHERE team_id = %s ORDER BY timestamp DESC LIMIT %s", (team_id, limit)
        )
        return [dict(row) for row in await cur.fetchall()]
