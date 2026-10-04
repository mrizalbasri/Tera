from app.domain.enums import ClaimStatus
from app.errors import InvalidStateTransitionError

CLAIM_STATUS_TRANSITIONS: dict[ClaimStatus, frozenset[ClaimStatus]] = {
    ClaimStatus.RECEIVED: frozenset({ClaimStatus.PROCESSING}),
    ClaimStatus.PROCESSING: frozenset(
        {
            ClaimStatus.NEEDS_CLARIFICATION,
            ClaimStatus.ESCALATED,
            ClaimStatus.APPROVED,
            ClaimStatus.REJECTED,
        }
    ),
    ClaimStatus.NEEDS_CLARIFICATION: frozenset(
        {ClaimStatus.PROCESSING, ClaimStatus.ESCALATED}
    ),
    ClaimStatus.ESCALATED: frozenset(
        {ClaimStatus.PROCESSING, ClaimStatus.APPROVED, ClaimStatus.REJECTED}
    ),
    ClaimStatus.APPROVED: frozenset(),
    ClaimStatus.REJECTED: frozenset(),
}


def can_transition(current: ClaimStatus, target: ClaimStatus) -> bool:
    return target in CLAIM_STATUS_TRANSITIONS[current]


def apply_transition(current: ClaimStatus, target: ClaimStatus) -> ClaimStatus:
    """Return the target status, raising if the transition is not legal."""
    if not can_transition(current, target):
        raise InvalidStateTransitionError("Claim status", current, target)
    return target
