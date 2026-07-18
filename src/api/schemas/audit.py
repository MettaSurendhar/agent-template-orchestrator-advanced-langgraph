from pydantic import BaseModel


class AuditEvent(BaseModel):
    """A single audit log entry."""

    id: str
    team_id: str | None
    user_id: str | None
    run_id: str | None
    event_type: str
    description: str
    timestamp: str


class AuditLogResponse(BaseModel):
    """Recent audit events for the team."""

    events: list[AuditEvent]
