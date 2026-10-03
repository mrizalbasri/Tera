"""Clarification conversation flow (FR-09).

Answering an open clarification stores the answer, records it in the claim's
conversation context, and resumes processing with a NEW run — earlier runs,
findings, and decisions are never overwritten.
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
from app.schemas.core import Clarification, ConversationEntry


class ClarificationService:
    def __init__(
        self,
        claims: ClaimRepository,
        clarifications: ClarificationRepository,
        context: ConversationContextRepository,
        audit: AuditRepository,
        process_resume,
    ) -> None:
        self._claims = claims
        self._clarifications = clarifications
        self._context = context
        self._audit = audit
        # Processing is injected as a callable to avoid a service cycle:
        # the resumed run reuses the extraction pipeline with resume=True.
        self._process_resume = process_resume

    def list_for_claim(self, claim_id: UUID) -> list[Clarification]:
        if self._claims.get(claim_id) is None:
            raise NotFoundError("Claim", str(claim_id))
        return list(self._clarifications.list_for_claim(claim_id))

    def answer(
        self, claim_id: UUID, clarification_id: UUID, *, answer: str, answered_by: str
    ) -> Clarification:
        if self._claims.get(claim_id) is None:
            raise NotFoundError("Claim", str(claim_id))
        clarification = next(
            (
                item
                for item in self._clarifications.list_for_claim(claim_id)
                if item.id == clarification_id
            ),
            None,
        )
        if clarification is None:
            raise NotFoundError("Clarification", str(clarification_id))
        if clarification.status != ClarificationStatus.OPEN:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "This clarification has already been answered.",
                409,
            )

        clean_answer = answer.strip()
        now = datetime.now(UTC)
        answered = clarification.model_copy(
            update={
                "answer": clean_answer,
                "status": ClarificationStatus.ANSWERED,
                "answered_at": now,
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
                "clarification_id": str(clarification_id),
                "code": clarification.code,
            },
            processing_run_id=clarification.processing_run_id,
        )
        return answered

    def resume(self, claim_id: UUID) -> dict:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))
        apply_transition(ClaimStatus(claim.status), ClaimStatus.PROCESSING)
        updated = claim.model_copy(
            update={
                "status": ClaimStatus.PROCESSING,
                "updated_at": datetime.now(UTC),
            }
        )
        self._claims.save(updated)
        return self._process_resume(claim_id)
