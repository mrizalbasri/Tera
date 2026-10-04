"""Human review endpoints (FR-10)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_review_service
from app.schemas.core import Claim, Decision, Review, Signal
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewDecisionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str = Field(min_length=1, max_length=2000)
    reviewer_reference: str = Field(min_length=1, max_length=100)


class ReviewQueueItem(BaseModel):
    review: Review
    claim: Claim
    decision: Decision | None = None
    signals: list[Signal] = []


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int


class ReviewDecisionResponse(BaseModel):
    claim: Claim
    decision: Decision
    review: Review


@router.get("", response_model=ReviewQueueResponse)
def list_open_reviews(
    service: ReviewService = Depends(get_review_service),
) -> ReviewQueueResponse:
    items = [
        ReviewQueueItem(
            review=item["review"],
            claim=item["claim"],
            decision=item["decision"],
            signals=item["signals"],
        )
        for item in service.list_open()
    ]
    return ReviewQueueResponse(items=items, total=len(items))


@router.post("/{claim_id}/decision", response_model=ReviewDecisionResponse)
def decide_review(
    claim_id: UUID,
    request: ReviewDecisionRequest,
    service: ReviewService = Depends(get_review_service),
) -> ReviewDecisionResponse:
    claim, decision, review = service.decide(
        claim_id,
        action=request.action,
        reason=request.reason,
        reviewer_reference=request.reviewer_reference,
    )
    return ReviewDecisionResponse(claim=claim, decision=decision, review=review)
