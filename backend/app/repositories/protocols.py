from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.schemas.core import (
    AuditEvent,
    Claim,
    Clarification,
    Decision,
    ExtractionAttempt,
    ExtractionResult,
    ProcessingRun,
    Receipt,
    Review,
)


class ClaimRepository(Protocol):
    def get(self, claim_id: UUID) -> Claim | None: ...

    def save(self, claim: Claim) -> Claim: ...

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]: ...

    def get_by_idempotency_key(self, key: str) -> Claim | None: ...

    def register_idempotency_key(self, key: str, claim_id: UUID) -> None: ...


class ReceiptRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Receipt]: ...

    def save(self, receipt: Receipt) -> Receipt: ...

    def find_claim_id_by_content_hash(self, content_hash: str) -> UUID | None: ...


class FileStorage(Protocol):
    def put(self, content: bytes, *, filename: str, media_type: str) -> str: ...

    def get(self, reference: str) -> bytes | None: ...

    def delete(self, reference: str) -> None: ...


class ProcessingRunRepository(Protocol):
    def get(self, run_id: UUID) -> ProcessingRun | None: ...

    def list_for_claim(self, claim_id: UUID) -> Sequence[ProcessingRun]: ...

    def latest_for_claim(self, claim_id: UUID) -> ProcessingRun | None: ...

    def save(self, run: ProcessingRun) -> ProcessingRun: ...


class ExtractionRepository(Protocol):
    def list_for_receipts(
        self, receipt_ids: Sequence[UUID]
    ) -> Sequence[ExtractionResult]: ...

    def save(self, result: ExtractionResult) -> ExtractionResult: ...


class ExtractionAttemptRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[ExtractionAttempt]: ...

    def save(self, claim_id: UUID, attempt: ExtractionAttempt) -> ExtractionAttempt: ...


class DecisionRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Decision]: ...

    def save(self, decision: Decision) -> Decision: ...


class ClarificationRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Clarification]: ...

    def latest_for_claim(self, claim_id: UUID) -> Clarification | None: ...

    def save(self, clarification: Clarification) -> Clarification: ...


class ReviewRepository(Protocol):
    def list_open(self) -> Sequence[Review]: ...

    def save(self, review: Review) -> Review: ...


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> AuditEvent: ...

    def list_for_aggregate(
        self, aggregate_type: str, aggregate_id: UUID
    ) -> Sequence[AuditEvent]: ...


class ReceiptQualityChecker(Protocol):
    def check(self, content: bytes, *, media_type: str) -> tuple[float, list[str]]: ...


class ReceiptExtractor(Protocol):
    def extract(
        self,
        *,
        receipt: Receipt,
        content: bytes,
        declared_amount: object | None,
        attempt: int,
    ) -> ExtractionResult: ...


class PolicyRetriever(Protocol):
    def retrieve(self, *, category: str, effective_date: object) -> object: ...


class DuplicateDetector(Protocol):
    def find_matches(self, claim: Claim) -> Sequence[UUID]: ...


class AnomalyScorer(Protocol):
    def score(self, claim: Claim) -> float: ...


class SensitiveDataMasker(Protocol):
    def mask(self, value: object) -> object: ...


class ReportExporter(Protocol):
    def export_csv(self, claims: Sequence[Claim]) -> str: ...
