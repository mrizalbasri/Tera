"""Human review endpoints (FR-10)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_review_service
from app.api.auth import require_admin
from app.schemas.core import Claim, Decision, Review, Signal
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"], dependencies=[Depends(require_admin)])


class ReviewDecisionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str = Field(min_length=1, max_length=2000)
    reviewer_reference: str | None = Field(default=None, max_length=100)


class ReviewQueueItem(BaseModel):
    review: Review
    claim: Claim
    decision: Decision | None = None
    signals: list[Signal] = []


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    limit: int = 100
    offset: int = 0


class ReviewDecisionResponse(BaseModel):
    claim: Claim
    decision: Decision
    review: Review


@router.get("", response_model=ReviewQueueResponse)
def list_open_reviews(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000_000),
    service: ReviewService = Depends(get_review_service),
) -> ReviewQueueResponse:
    items = [
        ReviewQueueItem(
            review=item["review"],
            claim=item["claim"],
            decision=item["decision"],
            signals=item["signals"],
        )
        for item in service.list_open(limit=limit, offset=offset)
    ]
    return ReviewQueueResponse(items=items, total=service.count_open(), limit=limit, offset=offset)


@router.post("/{claim_id}/decision", response_model=ReviewDecisionResponse)
def decide_review(
    claim_id: UUID,
    request: ReviewDecisionRequest,
    username: str = Depends(require_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewDecisionResponse:
    claim, decision, review = service.decide(
        claim_id,
        action=request.action,
        reason=request.reason,
        reviewer_reference=username,
    )
    return ReviewDecisionResponse(claim=claim, decision=decision, review=review)
