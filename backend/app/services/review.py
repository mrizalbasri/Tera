"""Human review of escalated claims (FR-10).

The reviewer's confirm/override is recorded as a NEW decision attributed to
the reviewer — the agent's escalated decision is preserved for audit.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.audit.events import record_audit_event
from app.domain.enums import ActorType, ClaimStatus, DecisionOutcome, ReviewStatus
from app.domain.transitions import apply_transition
from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    DecisionRepository,
    ReviewRepository,
    SignalRepository,
)
from app.schemas.core import Claim, Decision, Review
from app.services.processing import ClaimProcessingService

_DECISION_CLAIM_STATUS = {
    DecisionOutcome.APPROVED: ClaimStatus.APPROVED,
    DecisionOutcome.REJECTED: ClaimStatus.REJECTED,
}


class ReviewService:
    def __init__(
        self,
        claims: ClaimRepository,
        decisions: DecisionRepository,
        reviews: ReviewRepository,
        signals: SignalRepository,
        audit: AuditRepository,
        processing: ClaimProcessingService,
    ) -> None:
        self._claims = claims
        self._decisions = decisions
        self._reviews = reviews
        self._signals = signals
        self._audit = audit
        self._processing = processing

    def count_open(self) -> int:
        return self._reviews.count_open()

    def list_open(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        items: list[dict] = []
        reviews = self._reviews.page_open(limit=limit, offset=offset)
        ids = [review.claim_id for review in reviews]
        claims = {claim.id: claim for claim in self._claims.get_many(ids)}
        decisions = {}
        signals = {i: [] for i in ids}
        for decision in self._decisions.list_for_claims(ids):
            decisions[decision.claim_id] = decision
        for signal in self._signals.list_for_claims(ids):
            signals[signal.claim_id].append(signal)
        for review in reviews:
            claim = claims.get(review.claim_id)
            if claim is None:
                continue
            decision = decisions.get(review.claim_id)
            items.append(
                {
                    "review": review,
                    "claim": claim,
                    "decision": decision,
                    "signals": signals[review.claim_id],
                }
            )
        return items

    def decide(self, claim_id: UUID, *, action: Literal["approve", "reject"],
               reason: str, reviewer_reference: str) -> tuple[Claim, Decision, Review]:
        if not reason.strip() or not reviewer_reference.strip():
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Review reason and identity must not be blank.", 422)
        with self._processing.claim_lock(claim_id):
            self._processing.recover_claim(claim_id)
            self._pending_review(claim_id)
            return self._processing.resume_review(
                claim_id, lambda run_id: self._apply_decision(
                    claim_id, action=action, reason=reason,
                    reviewer_reference=reviewer_reference, processing_run_id=run_id,
                ),
            )

    def _pending_review(self, claim_id: UUID) -> tuple[Claim, Review]:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        review = next(
            (
                item
                for item in reversed(self._reviews.list_for_claim(claim_id))
                if item.status == ReviewStatus.OPEN
            ),
            None,
        )
        if review is None:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "Claim has no open review; only escalated claims can be reviewed.",
                409,
            )
        current_status = ClaimStatus(claim.status)
        if current_status is not ClaimStatus.ESCALATED:
            raise ApplicationError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Claim is no longer awaiting review.",
                409,
            )

        return claim, review

    def _apply_decision(self, claim_id: UUID, *, action: Literal["approve", "reject"],
                        reason: str, reviewer_reference: str,
                        processing_run_id: UUID) -> tuple[Claim, Decision, Review]:
        claim, review = self._pending_review(claim_id)
        current_status = ClaimStatus(claim.status)
        outcome = (
            DecisionOutcome.APPROVED if action == "approve" else DecisionOutcome.REJECTED
        )
        latest_decision = self._latest_decision(claim_id)
        now = datetime.now(UTC)
        decision = Decision(
            id=uuid4(),
            claim_id=claim_id,
            processing_run_id=processing_run_id,
            outcome=outcome,
            reason_codes=[f"reviewer_{action}"],
            explanation=reason.strip(),
            confidence=latest_decision.confidence if latest_decision else None,
            anomaly_score=latest_decision.anomaly_score if latest_decision else None,
            source_signal_ids=(
                latest_decision.source_signal_ids if latest_decision else []
            ),
            policy_version=latest_decision.policy_version if latest_decision else None,
            created_by=ActorType.REVIEWER,
            created_at=now,
        )
        self._decisions.save(decision)

        apply_transition(current_status, _DECISION_CLAIM_STATUS[outcome])
        updated_claim = self._claims.save(
            claim.model_copy(
                update={
                    "status": _DECISION_CLAIM_STATUS[outcome],
                    "current_decision_id": decision.id,
                    "updated_at": now,
                }
            )
        )
        decided_review = self._reviews.save(
            review.model_copy(
                update={
                    "status": ReviewStatus.DECIDED,
                    "reviewer_reference": reviewer_reference.strip(),
                    "action": action,
                    "reason": reason.strip(),
                    "decided_at": now,
                }
            )
        )
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim_id,
            event_type="review.decided",
            actor_type=ActorType.REVIEWER,
            safe_payload={
                "review_id": str(review.id),
                "action": action,
                "reviewer_reference": reviewer_reference.strip(),
                "decision_id": str(decision.id),
            },
            processing_run_id=decision.processing_run_id,
        )
        return updated_claim, decision, decided_review

    def _latest_decision(self, claim_id: UUID) -> Decision | None:
        decisions = self._decisions.list_for_claim(claim_id)
        return decisions[-1] if decisions else None
