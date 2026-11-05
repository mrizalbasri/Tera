"""Direct unit tests for ReviewService edge cases and methods."""

from datetime import UTC, datetime
from uuid import uuid4
import pytest

from app.domain.enums import ClaimStatus, ReviewStatus
from app.errors import ApplicationError, NotFoundError
from app.repositories.memory import InMemoryRepositories
from app.schemas.core import Claim, Review
from app.services.review import ReviewService


def _claim(status: ClaimStatus = ClaimStatus.ESCALATED) -> Claim:
    now = datetime.now(UTC)
    return Claim(
        id=uuid4(),
        employee_id="emp1",
        currency="IDR",
        status=status,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )


def _review(claim_id, status: ReviewStatus = ReviewStatus.OPEN) -> Review:
    now = datetime.now(UTC)
    return Review(
        id=uuid4(),
        claim_id=claim_id,
        status=status,
        created_at=now,
    )


def test_review_service_blank_reason_or_reviewer_raises_error():
    backend = InMemoryRepositories()
    service = ReviewService(
        claims=backend.claims,
        decisions=backend.decisions,
        reviews=backend.reviews,
        signals=backend.signals,
        audit=backend.audit,
        processing=None,
    )
    claim_id = uuid4()
    with pytest.raises(ApplicationError) as exc_info:
        service.decide(claim_id, action="approve", reason="", reviewer_reference="admin")
    assert exc_info.value.status_code == 422

    with pytest.raises(ApplicationError) as exc_info:
        service.decide(claim_id, action="approve", reason="Valid reason", reviewer_reference="")
    assert exc_info.value.status_code == 422


def test_review_service_missing_claim_raises_not_found():
    backend = InMemoryRepositories()
    service = ReviewService(
        claims=backend.claims,
        decisions=backend.decisions,
        reviews=backend.reviews,
        signals=backend.signals,
        audit=backend.audit,
        processing=None,
    )
    claim_id = uuid4()
    with pytest.raises(NotFoundError):
        service._pending_review(claim_id)


def test_review_service_no_open_review_raises_conflict():
    backend = InMemoryRepositories()
    claim = _claim(status=ClaimStatus.ESCALATED)
    backend.claims.save(claim)

    service = ReviewService(
        claims=backend.claims,
        decisions=backend.decisions,
        reviews=backend.reviews,
        signals=backend.signals,
        audit=backend.audit,
        processing=None,
    )
    with pytest.raises(ApplicationError) as exc_info:
        service._pending_review(claim.id)
    assert exc_info.value.status_code == 409


def test_review_service_not_escalated_raises_conflict():
    backend = InMemoryRepositories()
    claim = _claim(status=ClaimStatus.APPROVED)
    backend.claims.save(claim)
    review = _review(claim.id, status=ReviewStatus.OPEN)
    backend.reviews.save(review)

    service = ReviewService(
        claims=backend.claims,
        decisions=backend.decisions,
        reviews=backend.reviews,
        signals=backend.signals,
        audit=backend.audit,
        processing=None,
    )
    with pytest.raises(ApplicationError) as exc_info:
        service._pending_review(claim.id)
    assert exc_info.value.status_code == 409


def test_review_service_open_queue_page_detects_queue_change():
    backend = InMemoryRepositories()
    claim = _claim(status=ClaimStatus.ESCALATED)
    backend.claims.save(claim)
    review = _review(claim.id, status=ReviewStatus.OPEN)
    backend.reviews.save(review)

    service = ReviewService(
        claims=backend.claims,
        decisions=backend.decisions,
        reviews=backend.reviews,
        signals=backend.signals,
        audit=backend.audit,
        processing=None,
    )

    items, total, version = service.open_queue_page(limit=10, offset=0)
    assert total == 1
    assert len(items) == 1

    # Using wrong snapshot version raises 409
    with pytest.raises(ApplicationError) as exc_info:
        service.open_queue_page(limit=10, offset=0, snapshot="outdated-hash")
    assert exc_info.value.status_code == 409
