"""FastAPI dependency wiring for the storage backend and services."""

from functools import lru_cache
from threading import RLock
from weakref import WeakSet

from fastapi import Depends

from app.config import Settings, get_settings
from app.integrations.anomaly import RuleBasedAnomalyScorer
from app.integrations.claim_graph import graph_resources
from app.integrations.duplicate import AttributeDuplicateDetector
from app.integrations.llm import LlmReceiptExtractor
from app.integrations.masking import SensitiveDataMasker
from app.integrations.mock import MockReceiptExtractor
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.policy_rag import RagPolicyRetriever
from app.integrations.quality import FileQualityChecker
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
from app.services.processing import ClaimProcessingService
from app.services.intake import IntakeService
from app.services.review import ReviewService
from app.services.timeline import TimelineService
from app.services.validation import ValidationService


@lru_cache
def _memory_repositories() -> InMemoryRepositories:
    return InMemoryRepositories()


_sql_bundles: WeakSet[SqlRepositories] = WeakSet()


@lru_cache
def _sql_repositories(database_url: str) -> SqlRepositories:
    repositories = SqlRepositories(database_url)
    _sql_bundles.add(repositories)
    return repositories


def close_sql_repositories() -> None:
    for repositories in list(_sql_bundles):
        repositories.close()
    _sql_bundles.clear()
    _sql_repositories.cache_clear()


def _backend(settings: Settings):
    """Pick the storage backend bundle from request-scoped settings."""
    if settings.storage_backend == "sql":
        return _sql_repositories(settings.database_url)
    return _memory_repositories()


def get_claim_repository(settings: Settings = Depends(get_settings)) -> ClaimRepository:
    return _backend(settings).claims


def get_receipt_repository(settings: Settings = Depends(get_settings)) -> ReceiptRepository:
    return _backend(settings).receipts


def get_processing_run_repository(settings: Settings = Depends(get_settings)) -> ProcessingRunRepository:
    return _backend(settings).runs


def get_extraction_repository(settings: Settings = Depends(get_settings)) -> ExtractionRepository:
    return _backend(settings).extractions


def get_extraction_attempt_repository(settings: Settings = Depends(get_settings)) -> ExtractionAttemptRepository:
    return _backend(settings).attempts


def get_clarification_repository(settings: Settings = Depends(get_settings)) -> ClarificationRepository:
    return _backend(settings).clarifications


def get_audit_repository(settings: Settings = Depends(get_settings)) -> AuditRepository:
    return _backend(settings).audit


def get_validation_finding_repository(settings: Settings = Depends(get_settings)) -> ValidationFindingRepository:
    return _backend(settings).findings


def get_policy_evaluation_repository(settings: Settings = Depends(get_settings)) -> PolicyEvaluationRepository:
    return _backend(settings).evaluations


def get_signal_repository(settings: Settings = Depends(get_settings)) -> SignalRepository:
    return _backend(settings).signals


def get_decision_repository(settings: Settings = Depends(get_settings)) -> DecisionRepository:
    return _backend(settings).decisions


def get_claim_history_repository(settings: Settings = Depends(get_settings)) -> ClaimHistoryRepository:
    return _backend(settings).history


def get_review_repository(settings: Settings = Depends(get_settings)) -> ReviewRepository:
    return _backend(settings).reviews


def get_file_storage(settings: Settings = Depends(get_settings)) -> FileStorage:
    return _backend(settings).file_storage


def get_quality_checker() -> ReceiptQualityChecker:
    return FileQualityChecker()


def get_sensitive_data_masker() -> SensitiveDataMasker:
    return SensitiveDataMasker()


def get_receipt_extractor(
    settings: Settings = Depends(get_settings),
    masker: SensitiveDataMasker = Depends(get_sensitive_data_masker),
) -> ReceiptExtractor:
    if settings.provider_mode == "live":
        if not settings.llm_api_key:
            raise RuntimeError(
                "PROVIDER_MODE=live requires LLM_API_KEY in the environment."
            )
        return LlmReceiptExtractor(settings, masker)
    return MockReceiptExtractor()


def get_validation_service(
    settings: Settings = Depends(get_settings),
) -> ValidationService:
    return ValidationService(settings)


@lru_cache
def _rag_policy_retriever(index_path: str, model_cache: str) -> RagPolicyRetriever:
    return RagPolicyRetriever(index_path, model_cache)


_policy_adapter_lock = RLock()


def get_policy_retriever(settings: Settings = Depends(get_settings)) -> PolicyRetriever:
    if settings.policy_mode == "rag":
        with _policy_adapter_lock:
            return _rag_policy_retriever(settings.policy_index_path, settings.policy_model_cache)
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
) -> ClaimProcessingService:
    return ClaimProcessingService(
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
        graph_resources=graph_resources(_backend(settings), settings),
    )


def get_conversation_context_repository(settings: Settings = Depends(get_settings)) -> ConversationContextRepository:
    return _backend(settings).context


def get_clarification_service(
    claims: ClaimRepository = Depends(get_claim_repository),
    clarifications: ClarificationRepository = Depends(get_clarification_repository),
    context: ConversationContextRepository = Depends(
        get_conversation_context_repository
    ),
    audit: AuditRepository = Depends(get_audit_repository),
    extraction_service: ClaimProcessingService = Depends(get_extraction_service),
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
    receipts: ReceiptRepository = Depends(get_receipt_repository),
    runs: ProcessingRunRepository = Depends(get_processing_run_repository),
    attempts: ExtractionAttemptRepository = Depends(get_extraction_attempt_repository),
    extractions: ExtractionRepository = Depends(get_extraction_repository),
    findings: ValidationFindingRepository = Depends(get_validation_finding_repository),
    evaluations: PolicyEvaluationRepository = Depends(get_policy_evaluation_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    clarifications: ClarificationRepository = Depends(get_clarification_repository),
    reviews: ReviewRepository = Depends(get_review_repository),
    signals: SignalRepository = Depends(get_signal_repository),
    audit: AuditRepository = Depends(get_audit_repository),
) -> TimelineService:
    return TimelineService(
        claims,
        receipts,
        runs,
        attempts,
        extractions,
        findings,
        evaluations,
        decisions,
        clarifications,
        reviews,
        signals,
        audit,
    )


def get_review_service(
    claims: ClaimRepository = Depends(get_claim_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    reviews: ReviewRepository = Depends(get_review_repository),
    signals: SignalRepository = Depends(get_signal_repository),
    audit: AuditRepository = Depends(get_audit_repository),
    processing: ClaimProcessingService = Depends(get_extraction_service),
) -> ReviewService:
    return ReviewService(claims, decisions, reviews, signals, audit, processing)

