from typing import Literal

from pydantic import BaseModel, Field


class StartRunRequest(BaseModel):
    """Kick off a new orchestration run."""

    user_request: str
    artifacts: dict = Field(default_factory=dict)
    review_agents: list[str] = Field(
        default_factory=list, description="Agent names that should pause for human review before continuing."
    )


class PendingReview(BaseModel):
    """Details of the agent output currently awaiting human review, if any."""

    agent: str
    output: dict


class RunStatusResponse(BaseModel):
    """The current state of a run."""

    run_id: str
    status: str  # running | paused | completed | rejected | failed
    executed_agents: list[str]
    context: dict
    rationale: str | None = None
    final_summary: str | None = None
    pending_review: PendingReview | None = None
    audit_trail: list[dict]


class RunSummary(BaseModel):
    """A lightweight entry in the run list (ownership record, not full graph state)."""

    run_id: str
    user_request: str
    started_by_user_id: str
    status: str
    created_at: str


class RunListResponse(BaseModel):
    """All runs belonging to the current team."""

    runs: list[RunSummary]


class ResumeRequest(BaseModel):
    """Resume a paused run after human review."""

    action: Literal["approve", "edit", "reject"]
    edited_output: dict | None = None
    reason: str | None = None
