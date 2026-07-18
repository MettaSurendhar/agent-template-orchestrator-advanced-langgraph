from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from api import settings
from api.exceptions.custom_exceptions import APIException, api_exception_handler
from api.middleware.auth_middleware import auth_middleware
from api.orchestrator.graph import build_graph
from api.routers import audit, auth, reviews, runs
from api.utils import pg_util


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open both Postgres resources once at startup, run one-time setup, build the graph.

    Two separate connections are opened deliberately: `checkpointer` (AsyncPostgresSaver)
    owns LangGraph's own tables and is only ever touched via the compiled graph; `pg_pool`
    (a psycopg connection pool) owns this app's own tables (teams/users/runs-cache/audit)
    via `pg_util.py`. They may point at the same physical database (the default) or
    different ones (set CHECKPOINT_DATABASE_URL separately) — either way, keeping the
    connections separate keeps the two concerns from becoming entangled in code.
    """
    async with (
        AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer,
        AsyncConnectionPool(settings.database_url, open=False) as pg_pool,
    ):
        await pg_pool.open()
        await checkpointer.setup()
        await pg_util.setup(pg_pool)
        await pg_util.ensure_default_team(pg_pool, settings.default_team_id, "Default Team")

        app.state.graph = build_graph(checkpointer)
        app.state.pg_pool = pg_pool

        yield


app = FastAPI(title="Multi-Agent Orchestrator — Advanced Tier (LangGraph)", lifespan=lifespan)

app.middleware("http")(auth_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(auth.router)
app.include_router(runs.router)
app.include_router(reviews.router)
app.include_router(audit.router)


@app.get("/ping")
async def ping():
    """Health check."""
    return {"status": "OK"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=settings.app_host, port=settings.app_port, reload=True)
