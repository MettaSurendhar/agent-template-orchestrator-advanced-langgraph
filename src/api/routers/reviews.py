"""The review queue: a team-wide view of every run currently paused for review.

This is the feature that distinguishes this tier's review workflow from the POC/
intermediate tiers' — there, you check one run_id at a time. Here, a team lead (or
anyone on the team) can see everything awaiting review across the whole team in one call,
sourced from the `orchestrator_runs` status cache rather than querying every run's live
graph state — see `pg_util.py`'s module docstring for why that cache exists.
"""

from fastapi import APIRouter, Request

from api.schemas.reviews import PendingReviewItem, PendingReviewListResponse
from api.utils import pg_util

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/pending", response_model=PendingReviewListResponse)
async def list_pending_reviews(request: Request):
    """List every run in the team currently awaiting human review."""
    team_id = request.state.team_id
    pool = request.app.state.pg_pool

    rows = await pg_util.list_pending_reviews(pool, team_id)

    reviews = [
        PendingReviewItem(
            run_id=row["run_id"],
            user_request=row["user_request"],
            started_by_user_id=row["started_by_user_id"],
            pending_review_agent=row["pending_review_agent"],
            pending_review_output=row["pending_review_output"] or {},
            updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        )
        for row in rows
    ]

    return PendingReviewListResponse(reviews=reviews)
