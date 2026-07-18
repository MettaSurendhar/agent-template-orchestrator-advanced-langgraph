import uuid

from fastapi import APIRouter, Request
from langgraph.types import Command

from api.exceptions.custom_exceptions import APIException, ErrorCode
from api.orchestrator.run_utils import build_status_response
from api.orchestrator.state import OrchestratorState
from api.schemas.runs import ResumeRequest, RunListResponse, RunStatusResponse, RunSummary, StartRunRequest
from api.utils import pg_util

router = APIRouter(prefix="/runs", tags=["Runs"])


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


async def _require_team_ownership(pool, run_id: str, team_id: str) -> None:
    """Raise RUN_NOT_FOUND (not 403) if the run doesn't exist or belongs to another team.

    Any user on the owning team can access the run — this is team-level isolation, not
    per-user. Compare to the intermediate tier, where only the exact starting user could.
    """
    owner_team = await pg_util.get_run_team(pool, run_id)
    if owner_team is None or owner_team != team_id:
        raise APIException(status_code=404, error_code=ErrorCode.RUN_NOT_FOUND, message=f"No run found: {run_id}")


async def _sync_status_cache(pool, run_id: str, response: RunStatusResponse) -> None:
    """Update the run's cached status/pending-review fields after any state-changing call."""
    pending_agent = response.pending_review.agent if response.pending_review else None
    pending_output = response.pending_review.output if response.pending_review else None
    await pg_util.update_run_status(pool, run_id, response.status, pending_agent, pending_output)


@router.post("", response_model=RunStatusResponse)
async def start_run(request: Request, body: StartRunRequest):
    """Start a new orchestration run, owned by the authenticated user's team."""
    user_id = request.state.user_id
    team_id = request.state.team_id
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    graph = request.app.state.graph
    pool = request.app.state.pg_pool

    initial_state: OrchestratorState = {
        "run_id": run_id,
        "team_id": team_id,
        "user_id": user_id,
        "user_request": body.user_request,
        "artifacts": body.artifacts,
        "review_agents": body.review_agents,
        "context": {},
        "executed_agents": [],
        "audit_trail": [],
        "next_agent": "",
        "rationale": "",
        "agent_input": {},
        "status": "running",
        "final_summary": "",
    }

    await pg_util.register_run(pool, run_id, team_id, user_id, body.user_request)
    await pg_util.log_event(pool, team_id, user_id, run_id, "RUN_STARTED", body.user_request)

    try:
        await graph.ainvoke(initial_state, config=_config(run_id))
    except Exception as e:
        raise APIException(
            status_code=500,
            error_code=ErrorCode.GRAPH_EXECUTION_FAILED,
            message="The orchestration run failed.",
            details=str(e),
        ) from e

    snapshot = await graph.aget_state(_config(run_id))
    response = build_status_response(run_id, snapshot)
    await _sync_status_cache(pool, run_id, response)

    if response.status == "completed":
        await pg_util.log_event(pool, team_id, user_id, run_id, "RUN_COMPLETED", "Run completed")

    return response


@router.get("", response_model=RunListResponse)
async def list_runs(request: Request):
    """List the authenticated user's team's runs."""
    team_id = request.state.team_id
    pool = request.app.state.pg_pool
    rows = await pg_util.list_team_runs(pool, team_id)
    return RunListResponse(
        runs=[
            RunSummary(
                run_id=r["run_id"],
                user_request=r["user_request"],
                started_by_user_id=r["started_by_user_id"],
                status=r["status"],
                created_at=r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            )
            for r in rows
        ]
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run(request: Request, run_id: str):
    """Fetch the current status of a run belonging to your team."""
    team_id = request.state.team_id
    pool = request.app.state.pg_pool
    await _require_team_ownership(pool, run_id, team_id)

    graph = request.app.state.graph
    snapshot = await graph.aget_state(_config(run_id))
    return build_status_response(run_id, snapshot)


@router.post("/{run_id}/resume", response_model=RunStatusResponse)
async def resume_run(request: Request, run_id: str, body: ResumeRequest):
    """Resume a paused run belonging to your team, after human review.

    Any user on the owning team can resume it — not just whoever started it — since
    review is a team responsibility at this tier, not an individual one.
    """
    user_id = request.state.user_id
    team_id = request.state.team_id
    pool = request.app.state.pg_pool
    await _require_team_ownership(pool, run_id, team_id)

    graph = request.app.state.graph
    snapshot = await graph.aget_state(_config(run_id))

    if not snapshot.next:
        raise APIException(
            status_code=409, error_code=ErrorCode.RUN_NOT_PAUSED, message=f"Run {run_id} is not awaiting review."
        )

    if body.action == "edit" and body.edited_output is None:
        raise APIException(
            status_code=400,
            error_code=ErrorCode.INVALID_RESUME_ACTION,
            message="edited_output is required when action='edit'.",
        )

    resume_value = {"action": body.action, "edited_output": body.edited_output, "reason": body.reason}
    await pg_util.log_event(pool, team_id, user_id, run_id, "RUN_RESUMED", f"action={body.action}")

    try:
        await graph.ainvoke(Command(resume=resume_value), config=_config(run_id))
    except Exception as e:
        raise APIException(
            status_code=500,
            error_code=ErrorCode.GRAPH_EXECUTION_FAILED,
            message="Resuming the run failed.",
            details=str(e),
        ) from e

    snapshot = await graph.aget_state(_config(run_id))
    response = build_status_response(run_id, snapshot)
    await _sync_status_cache(pool, run_id, response)

    if response.status == "completed":
        await pg_util.log_event(pool, team_id, user_id, run_id, "RUN_COMPLETED", "Run completed")

    return response
