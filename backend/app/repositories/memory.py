from collections.abc import Sequence
from threading import RLock
from uuid import UUID

from app.schemas.core import (
    AuditEvent,
    Claim,
    Clarification,
    ExtractionAttempt,
    ExtractionResult,
    PolicyEvaluation,
    ProcessingRun,
    Receipt,
    Review,
    ValidationFinding,
)


class InMemoryClaimRepository:
    def __init__(self) -> None:
        self._claims: dict[UUID, Claim] = {}
        self._idempotency: dict[str, UUID] = {}
        self._lock = RLock()

    def get(self, claim_id: UUID) -> Claim | None:
        with self._lock:
            return self._claims.get(claim_id)

    def save(self, claim: Claim) -> Claim:
        with self._lock:
            self._claims[claim.id] = claim
        return claim

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]:
        with self._lock:
            claims = tuple(self._claims.values())
        if employee_id is None:
            return claims
        return tuple(claim for claim in claims if claim.employee_id == employee_id)

    def get_by_idempotency_key(self, key: str) -> Claim | None:
        with self._lock:
            claim_id = self._idempotency.get(key)
            return self._claims.get(claim_id) if claim_id else None

    def register_idempotency_key(self, key: str, claim_id: UUID) -> None:
        with self._lock:
            self._idempotency.setdefault(key, claim_id)


class InMemoryReceiptRepository:
    def __init__(self) -> None:
        self._receipts: dict[UUID, list[Receipt]] = {}
        self._content_hashes: dict[str, UUID] = {}
        self._lock = RLock()

    def save(self, receipt: Receipt) -> Receipt:
        with self._lock:
            self._receipts.setdefault(receipt.claim_id, []).append(receipt)
            self._content_hashes.setdefault(receipt.content_hash, receipt.claim_id)
        return receipt

    def list_for_claim(self, claim_id: UUID) -> Sequence[Receipt]:
        with self._lock:
            return tuple(self._receipts.get(claim_id, ()))

    def find_claim_id_by_content_hash(self, content_hash: str) -> UUID | None:
        with self._lock:
            return self._content_hashes.get(content_hash)


class InMemoryProcessingRunRepository:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[ProcessingRun]] = {}
        self._lock = RLock()

    def save(self, run: ProcessingRun) -> ProcessingRun:
        with self._lock:
            runs = self._runs.setdefault(run.claim_id, [])
            for index, existing in enumerate(runs):
                if existing.id == run.id:
                    runs[index] = run
                    break
            else:
                runs.append(run)
        return run

    def get(self, run_id: UUID) -> ProcessingRun | None:
        with self._lock:
            for runs in self._runs.values():
                for run in runs:
                    if run.id == run_id:
                        return run
        return None

    def list_for_claim(self, claim_id: UUID) -> Sequence[ProcessingRun]:
        with self._lock:
            return tuple(self._runs.get(claim_id, ()))

    def latest_for_claim(self, claim_id: UUID) -> ProcessingRun | None:
        with self._lock:
            runs = self._runs.get(claim_id, ())
            return runs[-1] if runs else None


class InMemoryExtractionRepository:
    def __init__(self) -> None:
        self._results: dict[UUID, list[ExtractionResult]] = {}
        self._lock = RLock()

    def save(self, result: ExtractionResult) -> ExtractionResult:
        with self._lock:
            self._results.setdefault(result.receipt_id, []).append(result)
        return result

    def list_for_receipts(self, receipt_ids: Sequence[UUID]) -> Sequence[ExtractionResult]:
        with self._lock:
            wanted = set(receipt_ids)
            return tuple(
                result
                for results in self._results.values()
                for result in results
                if result.receipt_id in wanted
            )


class InMemoryExtractionAttemptRepository:
    def __init__(self) -> None:
        self._attempts: dict[UUID, list[ExtractionAttempt]] = {}
        self._lock = RLock()

    def save(self, claim_id: UUID, attempt: ExtractionAttempt) -> ExtractionAttempt:
        with self._lock:
            self._attempts.setdefault(claim_id, []).append(attempt)
        return attempt

    def list_for_claim(self, claim_id: UUID) -> Sequence[ExtractionAttempt]:
        with self._lock:
            return tuple(self._attempts.get(claim_id, ()))


class InMemoryDecisionRepository:
    def __init__(self) -> None:
        self._decisions: dict[UUID, list[Decision]] = {}
        self._lock = RLock()

    def save(self, decision: Decision) -> Decision:
        with self._lock:
            self._decisions.setdefault(decision.claim_id, []).append(decision)
        return decision

    def list_for_claim(self, claim_id: UUID) -> Sequence[Decision]:
        with self._lock:
            return tuple(self._decisions.get(claim_id, ()))


class InMemoryClarificationRepository:
    def __init__(self) -> None:
        self._clarifications: dict[UUID, list[Clarification]] = {}
        self._lock = RLock()

    def save(self, clarification: Clarification) -> Clarification:
        with self._lock:
            self._clarifications.setdefault(clarification.claim_id, []).append(
                clarification
            )
        return clarification

    def list_for_claim(self, claim_id: UUID) -> Sequence[Clarification]:
        with self._lock:
            return tuple(self._clarifications.get(claim_id, ()))

    def latest_for_claim(self, claim_id: UUID) -> Clarification | None:
        with self._lock:
            items = self._clarifications.get(claim_id, ())
            return items[-1] if items else None


class InMemoryReviewRepository:
    def __init__(self) -> None:
        self._reviews: dict[UUID, Review] = {}
        self._lock = RLock()

    def save(self, review: Review) -> Review:
        with self._lock:
            self._reviews[review.id] = review
        return review

    def list_open(self) -> Sequence[Review]:
        with self._lock:
            return tuple(
                review for review in self._reviews.values() if review.status == "open"
            )


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            sequence = sum(
                1
                for existing in self._events
                if existing.aggregate_type == event.aggregate_type
                and existing.aggregate_id == event.aggregate_id
            )
            stored = event.model_copy(
                update={"sequence_number": max(sequence + 1, event.sequence_number)}
            )
            self._events.append(stored)
        return stored

    def list_for_aggregate(
        self, aggregate_type: str, aggregate_id: UUID
    ) -> Sequence[AuditEvent]:
        with self._lock:
            return tuple(
                event
                for event in self._events
                if event.aggregate_type == aggregate_type
                and event.aggregate_id == aggregate_id
            )


class InMemoryValidationFindingRepository:
    def __init__(self) -> None:
        self._findings: dict[UUID, list[ValidationFinding]] = {}
        self._lock = RLock()

    def save(self, finding: ValidationFinding) -> ValidationFinding:
        with self._lock:
            self._findings.setdefault(finding.claim_id, []).append(finding)
        return finding

    def list_for_claim(self, claim_id: UUID) -> Sequence[ValidationFinding]:
        with self._lock:
            return tuple(self._findings.get(claim_id, ()))


class InMemoryPolicyEvaluationRepository:
    def __init__(self) -> None:
        self._evaluations: dict[UUID, list[PolicyEvaluation]] = {}
        self._lock = RLock()

    def save(self, evaluation: PolicyEvaluation) -> PolicyEvaluation:
        with self._lock:
            self._evaluations.setdefault(evaluation.claim_id, []).append(evaluation)
        return evaluation

    def list_for_claim(self, claim_id: UUID) -> Sequence[PolicyEvaluation]:
        with self._lock:
            return tuple(self._evaluations.get(claim_id, ()))


class InMemoryRepositories:
    """Bundle of in-memory fakes used by the memory storage backend and tests."""

    def __init__(self) -> None:
        self.claims = InMemoryClaimRepository()
        self.receipts = InMemoryReceiptRepository()
        self.runs = InMemoryProcessingRunRepository()
        self.extractions = InMemoryExtractionRepository()
        self.attempts = InMemoryExtractionAttemptRepository()
        self.decisions = InMemoryDecisionRepository()
        self.clarifications = InMemoryClarificationRepository()
        self.reviews = InMemoryReviewRepository()
        self.audit = InMemoryAuditRepository()
        self.findings = InMemoryValidationFindingRepository()
        self.evaluations = InMemoryPolicyEvaluationRepository()


class InMemoryClaimStore:
    """Legacy aggregate store, kept until services move to the protocols above."""

    def __init__(self) -> None:
        self._claims: dict[UUID, Claim] = {}
        self._receipts: dict[UUID, list[Receipt]] = {}
        self._idempotency: dict[str, UUID] = {}
        self._content_hashes: dict[str, UUID] = {}
        self._content: dict[str, bytes] = {}
        self._extractions: dict[UUID, list[ExtractionResult]] = {}
        self._attempts: dict[UUID, list[ExtractionAttempt]] = {}
        self._processing_results: dict[UUID, dict[str, object]] = {}
        self._lock = RLock()

    def get(self, claim_id: UUID) -> Claim | None:
        with self._lock:
            return self._claims.get(claim_id)

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]:
        with self._lock:
            claims = tuple(self._claims.values())
        if employee_id is None:
            return claims
        return tuple(claim for claim in claims if claim.employee_id == employee_id)

    def save_claim(self, claim: Claim, *, idempotency_key: str | None = None) -> Claim:
        with self._lock:
            self._claims[claim.id] = claim
            self._receipts.setdefault(claim.id, [])
            if idempotency_key:
                self._idempotency[idempotency_key] = claim.id
        return claim

    def save_receipt(self, receipt: Receipt, *, content: bytes) -> Receipt:
        with self._lock:
            self._receipts.setdefault(receipt.claim_id, []).append(receipt)
            self._content_hashes[receipt.content_hash] = receipt.claim_id
            self._content[receipt.storage_reference] = content
        return receipt

    def list_receipts(self, claim_id: UUID) -> Sequence[Receipt]:
        with self._lock:
            return tuple(self._receipts.get(claim_id, ()))

    def get_by_idempotency_key(self, key: str) -> Claim | None:
        with self._lock:
            claim_id = self._idempotency.get(key)
            return self._claims.get(claim_id) if claim_id else None

    def get_claim_by_content_hash(self, content_hash: str) -> UUID | None:
        with self._lock:
            return self._content_hashes.get(content_hash)

    def get_content(self, storage_reference: str) -> bytes | None:
        with self._lock:
            return self._content.get(storage_reference)

    def save_extraction(self, result: ExtractionResult) -> ExtractionResult:
        with self._lock:
            self._extractions.setdefault(result.receipt_id, []).append(result)
        return result

    def list_extractions(self, claim_id: UUID) -> Sequence[ExtractionResult]:
        with self._lock:
            receipt_ids = {
                receipt.id for receipt in self._receipts.get(claim_id, ())
            }
            return tuple(
                result
                for receipt_id in receipt_ids
                for result in self._extractions.get(receipt_id, ())
            )

    def save_attempt(self, claim_id: UUID, attempt: ExtractionAttempt) -> None:
        with self._lock:
            self._attempts.setdefault(claim_id, []).append(attempt)

    def list_attempts(self, claim_id: UUID) -> Sequence[ExtractionAttempt]:
        with self._lock:
            return tuple(self._attempts.get(claim_id, ()))

    def get_processing_result(self, claim_id: UUID) -> dict[str, object] | None:
        with self._lock:
            return self._processing_results.get(claim_id)

    def save_processing_result(
        self, claim_id: UUID, result: dict[str, object]
    ) -> None:
        with self._lock:
            self._processing_results[claim_id] = result
