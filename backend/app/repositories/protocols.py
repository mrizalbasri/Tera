from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.schemas.core import (
    AuditEvent,
    Claim,
    Clarification,
    Decision,
    ProcessingRun,
    Receipt,
    Review,
)


class ClaimRepository(Protocol):
    def get(self, claim_id: UUID) -> Claim | None: ...

    def save(self, claim: Claim) -> Claim: ...

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]: ...


class ReceiptRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Receipt]: ...

    def save(self, receipt: Receipt) -> Receipt: ...


class ProcessingRunRepository(Protocol):
    def get(self, run_id: UUID) -> ProcessingRun | None: ...

    def list_for_claim(self, claim_id: UUID) -> Sequence[ProcessingRun]: ...

    def save(self, run: ProcessingRun) -> ProcessingRun: ...


class DecisionRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Decision]: ...

    def save(self, decision: Decision) -> Decision: ...


class ClarificationRepository(Protocol):
    def list_for_claim(self, claim_id: UUID) -> Sequence[Clarification]: ...

    def save(self, clarification: Clarification) -> Clarification: ...


class ReviewRepository(Protocol):
    def list_open(self) -> Sequence[Review]: ...

    def save(self, review: Review) -> Review: ...


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> AuditEvent: ...

    def list_for_aggregate(
        self, aggregate_type: str, aggregate_id: UUID
    ) -> Sequence[AuditEvent]: ...


class FileStorage(Protocol):
    def put(self, content: bytes, *, filename: str, media_type: str) -> str: ...

    def delete(self, storage_reference: str) -> None: ...


class ReceiptQualityChecker(Protocol):
    def check(self, content: bytes, *, media_type: str) -> tuple[float, list[str]]: ...


class ReceiptExtractor(Protocol):
    def extract(self, storage_reference: str) -> object: ...


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
