"""FastAPI dependency wiring for the storage backend and services."""

from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings
from app.integrations.anomaly import RuleBasedAnomalyScorer
from app.integrations.duplicate import AttributeDuplicateDetector
from app.integrations.mock import MockReceiptExtractor
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.quality import FileQualityChecker
from app.integrations.storage import InMemoryFileStorage
from app.repositories.memory import InMemoryRepositories
from app.repositories.sql import SqlRepositories
from app.repositories.protocols import (
    AnomalyScorer,
    AuditRepository,
    ClaimHistoryRepository,
    ClaimRepository,
    ClarificationRepository,
    DecisionRepository,
    DuplicateDetector,
    ExtractionAttemptRepository,
    ExtractionRepository,
    FileStorage,
    PolicyEvaluationRepository,
    PolicyEvaluator,
    PolicyRetriever,
    ProcessingRunRepository,
    ReceiptQualityChecker,
    ReceiptRepository,
    ReceiptExtractor,
    ReviewRepository,
    SignalRepository,
    ValidationFindingRepository,
    ConversationContextRepository,
)
from app.services.clarification import ClarificationService
from app.services.decision import DecisionEngine
from app.services.extraction import ExtractionService
from app.services.intake import IntakeService
from app.services.review import ReviewService
from app.services.timeline import TimelineService
from app.services.validation import ValidationService


@lru_cache
def _memory_repositories() -> InMemoryRepositories:
    return InMemoryRepositories()


@lru_cache
def _sql_repositories() -> SqlRepositories:
    return SqlRepositories(get_settings().database_url)


def _backend():
    """Pick the storage backend bundle from settings (memory | sql)."""
    if get_settings().storage_backend == "sql":
        return _sql_repositories()
    return _memory_repositories()


def get_claim_repository() -> ClaimRepository:
    return _backend().claims


def get_receipt_repository() -> ReceiptRepository:
    return _backend().receipts


def get_processing_run_repository() -> ProcessingRunRepository:
    return _backend().runs


def get_extraction_repository() -> ExtractionRepository:
    return _backend().extractions


def get_extraction_attempt_repository() -> ExtractionAttemptRepository:
    return _backend().attempts


def get_clarification_repository() -> ClarificationRepository:
    return _backend().clarifications


def get_audit_repository() -> AuditRepository:
    return _backend().audit


def get_validation_finding_repository() -> ValidationFindingRepository:
    return _backend().findings


def get_policy_evaluation_repository() -> PolicyEvaluationRepository:
    return _backend().evaluations


def get_signal_repository() -> SignalRepository:
    return _backend().signals


def get_decision_repository() -> DecisionRepository:
    return _backend().decisions


def get_claim_history_repository() -> ClaimHistoryRepository:
    return _backend().history


def get_review_repository() -> ReviewRepository:
    return _backend().reviews


def get_file_storage() -> FileStorage:
    return _backend().file_storage


def get_quality_checker() -> ReceiptQualityChecker:
    return FileQualityChecker()


def get_receipt_extractor() -> ReceiptExtractor:
    return MockReceiptExtractor()


def get_validation_service(
    settings: Settings = Depends(get_settings),
) -> ValidationService:
    return ValidationService(settings)


def get_policy_retriever() -> PolicyRetriever:
    return LocalPolicyRetriever()


def get_policy_evaluator() -> PolicyEvaluator:
    return LocalPolicyEvaluator()


def get_duplicate_detector(
    history: ClaimHistoryRepository = Depends(get_claim_history_repository),
    receipts: ReceiptRepository = Depends(get_receipt_repository),
    extractions: ExtractionRepository = Depends(get_extraction_repository),
) -> DuplicateDetector:
    return AttributeDuplicateDetector(history, receipts, extractions)


def get_anomaly_scorer() -> AnomalyScorer:
    return RuleBasedAnomalyScorer()


def get_decision_engine(
    settings: Settings = Depends(get_settings),
) -> DecisionEngine:
    return DecisionEngine(settings)



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
    findings: ValidationFindingRepository = Depends(get_validation_finding_repository),
    evaluations: PolicyEvaluationRepository = Depends(get_policy_evaluation_repository),
    signals: SignalRepository = Depends(get_signal_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    history: ClaimHistoryRepository = Depends(get_claim_history_repository),
    reviews: ReviewRepository = Depends(get_review_repository),
    audit: AuditRepository = Depends(get_audit_repository),
    duplicate_detector: DuplicateDetector = Depends(get_duplicate_detector),
    anomaly_scorer: AnomalyScorer = Depends(get_anomaly_scorer),
    extractor: ReceiptExtractor = Depends(get_receipt_extractor),
    validation: ValidationService = Depends(get_validation_service),
    policy_retriever: PolicyRetriever = Depends(get_policy_retriever),
    policy_evaluator: PolicyEvaluator = Depends(get_policy_evaluator),
    decider: DecisionEngine = Depends(get_decision_engine),
) -> ExtractionService:
    return ExtractionService(
        claims,
        receipts,
        storage,
        runs,
        extractions,
        attempts,
        clarifications,
        findings,
        evaluations,
        signals,
        decisions,
        history,
        reviews,
        audit,
        duplicate_detector,
        anomaly_scorer,
        extractor,
        validation,
        policy_retriever,
        policy_evaluator,
        decider,
        settings,
    )
def get_conversation_context_repository() -> ConversationContextRepository:
    return _backend().context


def get_clarification_service(
    claims: ClaimRepository = Depends(get_claim_repository),
    clarifications: ClarificationRepository = Depends(get_clarification_repository),
    context: ConversationContextRepository = Depends(
        get_conversation_context_repository
    ),
    audit: AuditRepository = Depends(get_audit_repository),
    extraction_service: ExtractionService = Depends(get_extraction_service),
) -> ClarificationService:
    return ClarificationService(
        claims,
        clarifications,
        context,
        audit,
        processing=extraction_service,
    )


def get_timeline_service(
    claims: ClaimRepository = Depends(get_claim_repository),
    runs: ProcessingRunRepository = Depends(get_processing_run_repository),
    attempts: ExtractionAttemptRepository = Depends(get_extraction_attempt_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    clarifications: ClarificationRepository = Depends(get_clarification_repository),
    reviews: ReviewRepository = Depends(get_review_repository),
    signals: SignalRepository = Depends(get_signal_repository),
) -> TimelineService:
    return TimelineService(
        claims, runs, attempts, decisions, clarifications, reviews, signals
    )


def get_review_service(
    claims: ClaimRepository = Depends(get_claim_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    reviews: ReviewRepository = Depends(get_review_repository),
    signals: SignalRepository = Depends(get_signal_repository),
    audit: AuditRepository = Depends(get_audit_repository),
) -> ReviewService:
    return ReviewService(claims, decisions, reviews, signals, audit)

