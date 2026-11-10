"""Clarification conversation flow (FR-09).

Answering an open clarification stores the answer, records it in the claim's
conversation context, and resumes processing with a NEW run — earlier runs,
findings, and decisions are never overwritten.

Repeated submission for an already-answered clarification is idempotent
(FR-09/M5): it returns the recorded outcome of the original answer's run
instead of erroring or creating another run.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.audit.events import record_audit_event
from app.domain.enums import ActorType, ClaimStatus, ClarificationStatus
from app.domain.transitions import apply_transition
from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    ClarificationRepository,
    ConversationContextRepository,
)
from app.schemas.core import Clarification, ConversationEntry, ProcessingOutcome
from app.services.processing import ClaimProcessingService
from app.services.clarification_fields import FIELD_LABELS, validate_confirmations


class ClarificationService:
    def __init__(
        self,
        claims: ClaimRepository,
        clarifications: ClarificationRepository,
        context: ConversationContextRepository,
        audit: AuditRepository,
        processing: ClaimProcessingService,
    ) -> None:
        self._claims = claims
        self._clarifications = clarifications
        self._context = context
        self._audit = audit
        # The extraction pipeline is injected directly; it never depends on
        # this service, so there is no import cycle.
        self._processing = processing

    def list_for_claim(self, claim_id: UUID) -> list[Clarification]:
        if self._claims.get(claim_id) is None:
            raise NotFoundError("Claim", str(claim_id))
        return list(self._clarifications.list_for_claim(claim_id))

    def submit_answer(self, claim_id: UUID, clarification_id: UUID, *,
                      answer: str, answered_by: str,
                      confirmed_fields: dict[str, str] | None = None) -> tuple[Clarification, ProcessingOutcome, bool]:
        with self._processing.claim_lock(claim_id):
            return self._submit_answer(claim_id, clarification_id,
                                       answer=answer, answered_by=answered_by, confirmed_fields=confirmed_fields)

    def _submit_answer(
        self,
        claim_id: UUID,
        clarification_id: UUID,
        *,
        answer: str,
        answered_by: str,
        confirmed_fields: dict[str, str] | None = None,
    ) -> tuple[Clarification, ProcessingOutcome, bool]:
        """Store the answer and resume, or replay when already answered.

        Returns (clarification, processing outcome, replayed).
        """
        if self._claims.get(claim_id) is None:
            raise NotFoundError("Claim", str(claim_id))
        clarification = next(
            (
                item
                for item in reversed(self._clarifications.list_for_claim(claim_id))
                if item.id == clarification_id
            ),
            None,
        )
        if clarification is None:
            raise NotFoundError("Clarification", str(clarification_id))

        if clarification.status == ClarificationStatus.ANSWERED:
            # Idempotent repeat: no mutation, no extra run — the recorded
            # outcome of the original answer's run is returned as-is.
            outcome = self._processing.process_claim(claim_id)
            return clarification, outcome, True

        claim = self._claims.get(claim_id)
        latest = self._clarifications.latest_for_claim(claim_id)
        if claim.status not in (ClaimStatus.NEEDS_CLARIFICATION, ClaimStatus.PROCESSING) or latest is None or latest.id != clarification.id:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Claim is not waiting for this clarification.", 409)
        self._processing.ensure_clarification_waiting(claim_id)
        if confirmed_fields is not None:
            confirmed_fields = validate_confirmations(clarification.fields, confirmed_fields)
            answer = "\n".join(f"{FIELD_LABELS[key]}: {value}" for key, value in confirmed_fields.items())
        with self._processing.resources.transaction():
            answered = self._record_answer(claim_id, clarification, answer, answered_by, confirmed_fields)
            self._processing.queue_clarification(claim_id)
        outcome = self._processing.resume_clarification(claim_id)
        return answered, outcome, False

    def _record_answer(self, claim_id: UUID, clarification: Clarification,
                       answer: str, answered_by: str,
                       confirmed_fields: dict[str, str] | None = None) -> Clarification:
        clean_answer = answer.strip()
        if not clean_answer:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Answer must not be blank.", 422)
        now = datetime.now(UTC)
        answered = clarification.model_copy(
            update={
                "answer": clean_answer,
                "status": ClarificationStatus.ANSWERED,
                "answered_at": now,
                "confirmed_fields": confirmed_fields or {},
                "receipt_revision": self._claims.get(claim_id).receipt_revision,
            }
        )
        self._clarifications.save(answered)
        self._context.append(
            ConversationEntry(
                claim_id=clarification.claim_id,
                role="agent",
                content=clarification.question,
                created_at=clarification.created_at,
            )
        )
        self._context.append(
            ConversationEntry(
                claim_id=claim_id,
                role="employee",
                content=f"{answered_by}: {clean_answer}",
                created_at=now,
            )
        )
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim_id,
            event_type="clarification.answered",
            actor_type=ActorType.EMPLOYEE,
            safe_payload={
                "clarification_id": str(clarification.id),
                "code": clarification.code,
            },
            processing_run_id=clarification.processing_run_id,
        )

        claim = self._claims.get(claim_id)
        if claim.status != ClaimStatus.PROCESSING:
            apply_transition(ClaimStatus(claim.status), ClaimStatus.PROCESSING)
        self._claims.save(
            claim.model_copy(
                update={
                    "status": ClaimStatus.PROCESSING,
                    "updated_at": datetime.now(UTC),
                }
            )
        )
        return answered
