"""FastAPI dependency wiring for the storage backend and services."""

from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings
from app.integrations.mock import MockReceiptExtractor
from app.integrations.quality import FileQualityChecker
from app.integrations.storage import InMemoryFileStorage
from app.repositories.memory import InMemoryRepositories
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    ClarificationRepository,
    ExtractionAttemptRepository,
    ExtractionRepository,
    FileStorage,
    ProcessingRunRepository,
    ReceiptQualityChecker,
    ReceiptRepository,
    ReceiptExtractor,
)
from app.services.extraction import ExtractionService
from app.services.intake import IntakeService


@lru_cache
def _repositories() -> InMemoryRepositories:
    if get_settings().storage_backend != "memory":
        raise NotImplementedError("Only the memory storage backend is wired.")
    return InMemoryRepositories()


@lru_cache
def _file_storage() -> InMemoryFileStorage:
    return InMemoryFileStorage()


def get_claim_repository() -> ClaimRepository:
    return _repositories().claims


def get_receipt_repository() -> ReceiptRepository:
    return _repositories().receipts


def get_processing_run_repository() -> ProcessingRunRepository:
    return _repositories().runs


def get_extraction_repository() -> ExtractionRepository:
    return _repositories().extractions


def get_extraction_attempt_repository() -> ExtractionAttemptRepository:
    return _repositories().attempts


def get_clarification_repository() -> ClarificationRepository:
    return _repositories().clarifications


def get_audit_repository() -> AuditRepository:
    return _repositories().audit


def get_file_storage() -> FileStorage:
    return _file_storage()


def get_quality_checker() -> ReceiptQualityChecker:
    return FileQualityChecker()


def get_receipt_extractor() -> ReceiptExtractor:
    return MockReceiptExtractor()


def get_intake_service(
    settings: Settings = Depends(get_settings),
    claims: ClaimRepository = Depends(get_claim_repository),
    receipts: ReceiptRepository = Depends(get_receipt_repository),
    storage: FileStorage = Depends(get_file_storage),
    quality: ReceiptQualityChecker = Depends(get_quality_checker),
    audit: AuditRepository = Depends(get_audit_repository),
) -> IntakeService:
    return IntakeService(claims, receipts, storage, quality, audit, settings)


def get_extraction_service(
    settings: Settings = Depends(get_settings),
    claims: ClaimRepository = Depends(get_claim_repository),
    receipts: ReceiptRepository = Depends(get_receipt_repository),
    storage: FileStorage = Depends(get_file_storage),
    runs: ProcessingRunRepository = Depends(get_processing_run_repository),
    extractions: ExtractionRepository = Depends(get_extraction_repository),
    attempts: ExtractionAttemptRepository = Depends(get_extraction_attempt_repository),
    clarifications: ClarificationRepository = Depends(get_clarification_repository),
    audit: AuditRepository = Depends(get_audit_repository),
    extractor: ReceiptExtractor = Depends(get_receipt_extractor),
) -> ExtractionService:
    return ExtractionService(
        claims,
        receipts,
        storage,
        runs,
        extractions,
        attempts,
        clarifications,
        audit,
        extractor,
        settings,
    )
