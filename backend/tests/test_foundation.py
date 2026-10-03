from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import ClaimStatus
from app.domain.transitions import can_transition
from app.schemas.core import ClaimCreate
from app.schemas.errors import ErrorResponse


def test_claim_status_transitions_follow_domain_rules() -> None:
    assert can_transition(ClaimStatus.RECEIVED, ClaimStatus.PROCESSING)
    assert can_transition(ClaimStatus.PROCESSING, ClaimStatus.ESCALATED)
    assert not can_transition(ClaimStatus.APPROVED, ClaimStatus.REJECTED)


def test_claim_create_rejects_invalid_amount_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ClaimCreate(
            employee_id="employee-1",
            declared_amount=0,
            unexpected="not allowed",
        )


def test_error_response_serializes_stable_shape() -> None:
    response = ErrorResponse(
        code="not_found",
        message="Claim was not found.",
        details={"claim_id": str(uuid4())},
    )

    assert response.model_dump()["code"] == "not_found"
    assert response.model_dump()["details"]["claim_id"]
