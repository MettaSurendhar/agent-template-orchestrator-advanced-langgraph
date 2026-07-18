from pydantic import BaseModel


class PendingReviewItem(BaseModel):
    """A single run currently paused for review, as seen from the team-wide queue."""

    run_id: str
    user_request: str
    started_by_user_id: str
    pending_review_agent: str
    pending_review_output: dict
    updated_at: str


class PendingReviewListResponse(BaseModel):
    """Every run in the team currently awaiting review, oldest first."""

    reviews: list[PendingReviewItem]
