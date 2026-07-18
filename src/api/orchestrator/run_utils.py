"""Turn a LangGraph StateSnapshot into the API's RunStatusResponse shape.

Centralized here since /runs, /runs/{id}, and /runs/{id}/resume all need to build the
same response shape from a snapshot after driving the graph forward.
"""

from api.schemas.runs import PendingReview, RunStatusResponse


def build_status_response(run_id: str, snapshot) -> RunStatusResponse:
    """Build a RunStatusResponse from a LangGraph StateSnapshot."""
    values = snapshot.values

    pending_review = None
    if snapshot.tasks:
        for task in snapshot.tasks:
            if task.interrupts:
                payload = task.interrupts[0].value
                pending_review = PendingReview(agent=payload["agent"], output=payload["output"])
                break

    status = values.get("status", "running")
    if pending_review:
        status = "paused"
    elif not snapshot.next and status == "running":
        # Graph has no more pending nodes and nothing overrode status -> treat as completed.
        status = "completed"

    return RunStatusResponse(
        run_id=run_id,
        status=status,
        executed_agents=values.get("executed_agents", []),
        context=values.get("context", {}),
        rationale=values.get("rationale"),
        final_summary=values.get("final_summary") or None,
        pending_review=pending_review,
        audit_trail=values.get("audit_trail", []),
    )
