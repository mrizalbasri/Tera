from collections import deque
from collections.abc import Sequence
from threading import RLock
from uuid import UUID

from app.integrations.storage import InMemoryFileStorage
from app.schemas.core import (
    AuditEvent,
    Claim,
    Clarification,
    ConversationEntry,
    Decision,
    ExtractionAttempt,
    ExtractionResult,
    PolicyEvaluation,
    ProcessingRun,
    Receipt,
    Review,
    Signal,
    ValidationFinding,
)


class InMemoryClaimRepository:
    def get_many(self, claim_ids):
        with self._lock:
            return tuple(self._claims[i] for i in claim_ids if i in self._claims)
    def page(self, filters, *, limit: int, offset: int):
        return tuple(c for c in self.list(employee_id=filters.employee_id) if filters.matches(c))[offset:offset + limit]

    def count(self, filters) -> int:
        return sum(filters.matches(c) for c in self.list(employee_id=filters.employee_id))
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

    def reserve_idempotency_key(self, key: str, claim_id: UUID) -> bool:
        with self._lock:
            if key in self._idempotency:
                return False
            self._idempotency[key] = claim_id
            return True


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
    def pending_claim_ids(self, *, limit: int, offset: int = 0):
        with self._lock:
            return tuple(k for k, records in self._runs.items() if records and records[-1].status in ("running", "queued"))[offset:offset + limit]
    def list_for_claims(self, claim_ids):
        return tuple(record for claim_id in claim_ids for record in self.list_for_claim(claim_id))
    def __init__(self) -> None:
        self._runs: dict[UUID, list[ProcessingRun]] = {}
        self._run_keys: dict[str, UUID] = {}
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

    def reserve_run_key(self, key: str, run_id: UUID) -> bool:
        with self._lock:
            if key in self._run_keys:
                return False
            self._run_keys[key] = run_id
            return True

    def get_run_by_key(self, key: str) -> ProcessingRun | None:
        with self._lock:
            run_id = self._run_keys.get(key)
        if run_id is None:
            return None
        return self.get(run_id)


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
    def list_for_claims(self, claim_ids):
        return tuple(record for claim_id in claim_ids for record in self.list_for_claim(claim_id))
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
            items = self._clarifications.setdefault(clarification.claim_id, [])
            for index, existing in enumerate(items):
                if existing.id == clarification.id:
                    items[index] = clarification
                    break
            else:
                items.append(clarification)
        return clarification

    def list_for_claim(self, claim_id: UUID) -> Sequence[Clarification]:
        with self._lock:
            return tuple(self._clarifications.get(claim_id, ()))

    def latest_for_claim(self, claim_id: UUID) -> Clarification | None:
        with self._lock:
            items = self._clarifications.get(claim_id, ())
            return items[-1] if items else None


class InMemoryReviewRepository:
    def page_open(self, *, limit: int, offset: int):
        return self.list_open()[offset:offset + limit]

    def count_open(self) -> int:
        return len(self.list_open())
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

    def list_for_claim(self, claim_id: UUID) -> Sequence[Review]:
        with self._lock:
            return tuple(
                review
                for review in self._reviews.values()
                if review.claim_id == claim_id
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


class InMemorySignalRepository:
    def list_for_claims(self, claim_ids):
        return tuple(record for claim_id in claim_ids for record in self.list_for_claim(claim_id))
    def __init__(self) -> None:
        self._signals: dict[UUID, list[Signal]] = {}
        self._lock = RLock()

    def save(self, signal: Signal) -> Signal:
        with self._lock:
            self._signals.setdefault(signal.claim_id, []).append(signal)
        return signal

    def list_for_claim(self, claim_id: UUID) -> Sequence[Signal]:
        with self._lock:
            return tuple(self._signals.get(claim_id, ()))


class InMemoryClaimHistoryRepository:
    """Employee- and vendor-scoped claim history views (FR-15)."""

    def __init__(
        self,
        claims: InMemoryClaimRepository,
        receipts: InMemoryReceiptRepository,
        extractions: InMemoryExtractionRepository,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._extractions = extractions

    def list_for_employee(
        self, employee_id: str, *, exclude_claim_id: UUID | None = None
    ) -> Sequence[Claim]:
        return tuple(
            claim
            for claim in self._claims.list(employee_id=employee_id)
            if claim.id != exclude_claim_id
        )

    def list_for_vendor(
        self, vendor: str, *, exclude_claim_id: UUID | None = None
    ) -> Sequence[Claim]:
        wanted = vendor.strip().lower()
        matched: list[Claim] = []
        for claim in self._claims.list():
            if claim.id == exclude_claim_id:
                continue
            receipt_ids = [
                receipt.id for receipt in self._receipts.list_for_claim(claim.id)
            ]
            if any(
                str(result.vendor.value).strip().lower() == wanted
                for result in self._extractions.list_for_receipts(receipt_ids)
            ):
                matched.append(claim)
        return tuple(matched)


class InMemoryConversationContextRepository:
    """Bounded per-claim conversation memory (FR-15)."""

    MAX_ENTRIES = 20

    def __init__(self) -> None:
        self._context: dict[UUID, deque[ConversationEntry]] = {}
        self._lock = RLock()

    def append(self, entry: ConversationEntry) -> ConversationEntry:
        with self._lock:
            entries = self._context.setdefault(
                entry.claim_id,
                deque(maxlen=self.MAX_ENTRIES),
            )
            entries.append(entry)
        return entry

    def list_for_claim(self, claim_id: UUID) -> Sequence[ConversationEntry]:
        with self._lock:
            return tuple(self._context.get(claim_id, ()))


class InMemoryRepositories:
    """Bundle of in-memory fakes used by the memory storage backend and tests."""

    def __init__(self) -> None:
        from app.services.rate_limit import MemoryRateLimiter
        from app.repositories.operational import MemoryOperationalStore

        self.operational = MemoryOperationalStore()
        self.rate_limiter = MemoryRateLimiter()
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
        self.signals = InMemorySignalRepository()
        self.context = InMemoryConversationContextRepository()
        self.file_storage = InMemoryFileStorage()

    @property
    def history(self) -> InMemoryClaimHistoryRepository:
        return InMemoryClaimHistoryRepository(self.claims, self.receipts, self.extractions)


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
