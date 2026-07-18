from fastapi import APIRouter, Request

from api.schemas.audit import AuditEvent, AuditLogResponse
from api.utils import pg_util

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=AuditLogResponse)
async def get_audit_log(request: Request, limit: int = 100):
    """Fetch the current team's recent audit events (registrations, logins, run lifecycle events)."""
    team_id = request.state.team_id
    pool = request.app.state.pg_pool
    rows = await pg_util.get_audit_log(pool, team_id=team_id, limit=limit)

    events = [
        AuditEvent(
            id=row["id"],
            team_id=row["team_id"],
            user_id=row["user_id"],
            run_id=row["run_id"],
            event_type=row["event_type"],
            description=row["description"],
            timestamp=row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
        )
        for row in rows
    ]

    return AuditLogResponse(events=events)
