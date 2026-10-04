import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.audit.events import record_audit_event
from app.config import Settings
from app.domain.enums import (
    ActorType,
    ClaimStatus,
    ClarificationStatus,
    DecisionOutcome,
    ProcessingRunStatus,
    ReviewStatus,
)
from app.domain.transitions import apply_transition
from app.errors import ApplicationError, ErrorCode, NotFoundError
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
    ReceiptExtractor,
    ReceiptRepository,
    ReviewRepository,
    SignalRepository,
    ValidationFindingRepository,
)
from app.schemas.core import (
    Clarification,
    ClarificationRequest,
    Claim,
    Decision,
    ExtractionAttempt,
    ExtractionResult,
    PolicyEvaluation,
    ProcessingOutcome,
    ProcessingRun,
    Review,
    Signal,
    ValidationFinding,
)
from app.services.decision import DecisionEngine
from app.services.validation import SUPPORTED_CATEGORIES, ValidationService

_DECISION_CLAIM_STATUS = {
    DecisionOutcome.APPROVED: ClaimStatus.APPROVED,
    DecisionOutcome.REJECTED: ClaimStatus.REJECTED,
    DecisionOutcome.ESCALATED: ClaimStatus.ESCALATED,
    DecisionOutcome.NEEDS_CLARIFICATION: ClaimStatus.NEEDS_CLARIFICATION,
}
_DECISION_RUN_STATUS = {
    DecisionOutcome.APPROVED: ProcessingRunStatus.SUCCEEDED,
    DecisionOutcome.REJECTED: ProcessingRunStatus.SUCCEEDED,
    DecisionOutcome.ESCALATED: ProcessingRunStatus.ESCALATED,
    DecisionOutcome.NEEDS_CLARIFICATION: ProcessingRunStatus.NEEDS_CLARIFICATION,
}

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "0.1.0"
_EXTRACTION_USER_MESSAGE = (
    "Receipt extraction failed; please upload a clearer receipt."
)
_CONFIDENCE_LOW_MESSAGE = (
    "Please upload a clearer receipt where the vendor, date, and total are readable."
)
_CONFIDENCE_FIELDS = ("vendor", "receipt_date", "total", "currency", "category")


class ExtractionService:
    def __init__(
        self,
        claims: ClaimRepository,
        receipts: ReceiptRepository,
        storage: FileStorage,
        runs: ProcessingRunRepository,
        extractions: ExtractionRepository,
        attempts: ExtractionAttemptRepository,
        clarifications: ClarificationRepository,
        findings: ValidationFindingRepository,
        evaluations: PolicyEvaluationRepository,
        signals: SignalRepository,
        decisions: DecisionRepository,
        history: ClaimHistoryRepository,
        reviews: ReviewRepository,
        audit: AuditRepository,
        duplicate_detector: DuplicateDetector,
        anomaly_scorer: AnomalyScorer,
        extractor: ReceiptExtractor,
        validation: ValidationService,
        policy_retriever: PolicyRetriever,
        policy_evaluator: PolicyEvaluator,
        decider: DecisionEngine,
        settings: Settings,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._storage = storage
        self._runs = runs
        self._extractions = extractions
        self._attempts = attempts
        self._clarifications = clarifications
        self._findings = findings
        self._evaluations = evaluations
        self._signals = signals
        self._decisions = decisions
        self._history = history
        self._reviews = reviews
        self._audit = audit
        self._duplicate_detector = duplicate_detector
        self._anomaly_scorer = anomaly_scorer
        self._extractor = extractor
        self._validation = validation
        self._policy_retriever = policy_retriever
        self._policy_evaluator = policy_evaluator
        self._decider = decider
        self._settings = settings

    def process_claim(self, claim_id: UUID, *, resume: bool = False) -> ProcessingOutcome:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        latest_run = self._runs.latest_for_claim(claim_id)
        if (
            not resume
            and latest_run is not None
            and latest_run.status
            in (
                ProcessingRunStatus.SUCCEEDED,
                ProcessingRunStatus.NEEDS_CLARIFICATION,
                ProcessingRunStatus.ESCALATED,
            )
        ):
            # Repetition without new input replays the recorded run instead of
            # creating a conflicting one (M6 reliability rule).
            return self._replay(claim_id, latest_run)
        if latest_run is not None and latest_run.status == ProcessingRunStatus.RUNNING:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "A processing run is already in progress.",
                409,
            )

        current_status = ClaimStatus(claim.status)
        if current_status is ClaimStatus.RECEIVED:
            claim = self._transition_claim(claim, ClaimStatus.PROCESSING)
        elif current_status is ClaimStatus.PROCESSING and (
            resume
            or (
                latest_run is not None
                and latest_run.status == ProcessingRunStatus.FAILED
            )
        ):
            pass
        else:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "Claim cannot be processed in its current state.",
                409,
            )

        run = ProcessingRun(
            id=uuid4(),
            claim_id=claim_id,
            status=ProcessingRunStatus.QUEUED,
            pipeline_version=PIPELINE_VERSION,
            started_at=None,
            completed_at=None,
            retry_count=len(self._runs.list_for_claim(claim_id)),
            error_code=None,
        )
        self._runs.save(run)
        logger.info("processing run %s queued for claim %s", run.id, claim_id)
        return self._execute_run(claim, run)

    def _execute_run(self, claim: Claim, run: ProcessingRun) -> ProcessingOutcome:
        started_at = datetime.now(UTC)
        run = run.model_copy(
            update={"status": ProcessingRunStatus.RUNNING, "started_at": started_at}
        )
        self._runs.save(run)

        receipts = list(self._receipts.list_for_claim(claim.id))
        if not receipts:
            return self._fail_run(
                run,
                ErrorCode.RECEIPT_REQUIRED,
                "Claim has no receipt to extract.",
                422,
            )

        attempts: list[ExtractionAttempt] = []
        for attempt_number in range(1, self._settings.max_processing_retries + 2):
            preprocessing = ["normalize_document"] if attempt_number > 1 else []
            attempt_results: list[ExtractionResult] = []
            errors: list[str] = []
            for receipt in receipts:
                content = self._storage.get(receipt.storage_reference)
                if content is None:
                    errors.append(ErrorCode.RECEIPT_CONTENT_UNAVAILABLE)
                    continue
                try:
                    result = self._extractor.extract(
                        receipt=receipt,
                        content=content,
                        declared_amount=claim.declared_amount,
                        attempt=attempt_number,
                    )
                except ApplicationError as exc:
                    errors.append(exc.code)
                    continue
                except ValidationError as exc:
                    logger.warning(
                        "provider output failed validation for receipt %s: %s",
                        receipt.id,
                        exc,
                    )
                    errors.append(ErrorCode.MALFORMED_EXTRACTION)
                    continue
                attempt_results.append(result)

            if errors:
                self._save_attempt(
                    run,
                    attempt_number,
                    preprocessing,
                    confidence={},
                    error_code=errors[0],
                )
                return self._fail_run(
                    run, errors[0], _EXTRACTION_USER_MESSAGE, 502, attempts
                )

            confidence = _min_confidence_map(attempt_results)
            attempts.append(
                self._save_attempt(
                    run,
                    attempt_number,
                    preprocessing,
                    confidence=confidence,
                    extraction_id=attempt_results[0].id if attempt_results else None,
                )
            )
            threshold = Decimal(str(self._settings.extraction_confidence_threshold))
            if all(value >= threshold for value in confidence.values()):
                saved = [
                    self._extractions.save(
                        result.model_copy(update={"processing_run_id": run.id})
                    )
                    for result in attempt_results
                ]
                findings = self._validate_extraction(claim, saved)
                participants, _answered = self._answered_participants(claim.id)
                evaluations = self._evaluate_policy(
                    claim, saved, run, attempts, participants
                )
                total = max(
                    (
                        _as_decimal(result.total.value) or Decimal("0")
                        for result in saved
                    ),
                    default=Decimal("0"),
                )
                signals = self._detect_signals(claim, receipts, total, run)
                decision = self._decider.decide(
                    claim=claim,
                    total=total,
                    confidence=min(confidence.values()) if confidence else None,
                    findings=findings,
                    evaluations=evaluations,
                    signals=signals,
                    policy_version=(
                        evaluations[0].policy_version if evaluations else None
                    ),
                    processing_run_id=run.id,
                    answered_codes=self._answered_codes(claim.id),
                )
                self._decisions.save(decision)
                claim = self._transition_claim(
                    claim, _DECISION_CLAIM_STATUS[decision.outcome]
                )
                claim = self._claims.save(
                    claim.model_copy(update={"current_decision_id": decision.id})
                )
                clarification = None
                if decision.outcome == DecisionOutcome.NEEDS_CLARIFICATION:
                    clarification = self._record_data_clarification(
                        claim, decision, run
                    )
                elif decision.outcome == DecisionOutcome.ESCALATED:
                    self._open_review(claim, run)
                self._complete_run(
                    run,
                    _DECISION_RUN_STATUS[decision.outcome],
                    attempts,
                    error_code=None,
                )
                return ProcessingOutcome(
                    claim=claim,
                    extractions=saved,
                    attempts=attempts,
                    clarification=clarification,
                    validation_findings=findings,
                    policy_evaluations=evaluations,
                    decision=decision,
                )

        return self._request_clarification(claim, run, attempts, confidence)

    def _validate_extraction(
        self, claim: Claim, saved: list[ExtractionResult]
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for result in saved:
            findings.extend(
                self._validation.validate(
                    claim=claim,
                    extraction=result,
                    processing_run_id=result.processing_run_id or claim.id,
                )
            )
        for finding in findings:
            self._findings.save(finding)
        return findings

    def _evaluate_policy(
        self,
        claim: Claim,
        saved: list[ExtractionResult],
        run: ProcessingRun,
        attempts: list[ExtractionAttempt],
        participants: int = 1,
    ) -> list[PolicyEvaluation]:
        evaluations: list[PolicyEvaluation] = []
        for result in saved:
            category = str(result.category.value or "")
            if category not in SUPPORTED_CATEGORIES:
                # Validation already flags the unknown category as blocking;
                # there is no policy to retrieve for it.
                continue
            try:
                policy = self._policy_retriever.retrieve(
                    category=category,
                    effective_date=_as_date(result.receipt_date.value),
                )
            except ApplicationError:
                return self._fail_run(
                    run,
                    ErrorCode.POLICY_UNAVAILABLE,
                    "Policy retrieval failed; the claim cannot be approved "
                    "automatically.",
                    503,
                    attempts,
                )
            for evaluation in self._policy_evaluator.evaluate(
                claim=claim,
                extraction=result,
                policy=policy,
                processing_run_id=run.id,
                participants=participants,
            ):
                self._evaluations.save(evaluation)
                evaluations.append(evaluation)
        return evaluations

    def _answered_codes(self, claim_id: UUID) -> set[str]:
        """Codes of clarifications that already received an answer."""
        return {
            clarification.code
            for clarification in self._clarifications.list_for_claim(claim_id)
            if clarification.status == ClarificationStatus.ANSWERED
        }

    def _answered_participants(self, claim_id: UUID) -> tuple[int, bool]:
        """Participant count from the latest answered clarification, if any."""
        for clarification in reversed(self._clarifications.list_for_claim(claim_id)):
            if (
                clarification.status == ClarificationStatus.ANSWERED
                and "participant_count" in clarification.fields
                and clarification.answer
            ):
                try:
                    return max(int(str(clarification.answer).strip()), 1), True
                except ValueError:
                    continue
        return 1, False

    def _open_review(self, claim: Claim, run: ProcessingRun) -> None:
        review = Review(
            id=uuid4(),
            claim_id=claim.id,
            status=ReviewStatus.OPEN,
            reviewer_reference=None,
            action=None,
            reason=None,
            created_at=datetime.now(UTC),
            decided_at=None,
        )
        self._reviews.save(review)
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim.id,
            event_type="review.opened",
            actor_type=ActorType.AGENT,
            safe_payload={"run_id": str(run.id)},
            processing_run_id=run.id,
        )

    def _detect_signals(
        self,
        claim: Claim,
        receipts: list,
        total: Decimal,
        run: ProcessingRun,
    ) -> list[Signal]:
        signals: list[Signal] = self._duplicate_detector.find_matches(
            claim=claim, receipts=receipts, processing_run_id=run.id
        )
        for signal in signals:
            self._signals.save(signal)
        history = self._history.list_for_employee(
            claim.employee_id, exclude_claim_id=claim.id
        )
        anomaly = self._anomaly_scorer.score(
            claim=claim, total=total, history=history, processing_run_id=run.id
        )
        self._signals.save(anomaly)
        signals.append(anomaly)
        return signals

    def _record_data_clarification(
        self, claim: Claim, decision: Decision, run: ProcessingRun
    ) -> ClarificationRequest:
        clarification_fields = {
            "participant_count_required": ["participant_count"],
            "business_trip_evidence_required": ["business_trip_evidence"],
        }
        code = next(
            (
                reason
                for reason in decision.reason_codes
                if reason in clarification_fields
            ),
            "invalid_claim_data",
        )
        clarification = Clarification(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=run.id,
            code=code,
            fields=clarification_fields.get(code, list(decision.reason_codes)),
            question=decision.explanation,
            answer=None,
            status=ClarificationStatus.OPEN,
            created_at=datetime.now(UTC),
            answered_at=None,
        )
        self._clarifications.save(clarification)
        return ClarificationRequest(
            code=clarification.code,
            message=clarification.question,
            fields=clarification.fields,
        )

    def _request_clarification(
        self,
        claim: Claim,
        run: ProcessingRun,
        attempts: list[ExtractionAttempt],
        confidence: dict[str, Decimal],
    ) -> ProcessingOutcome:
        now = datetime.now(UTC)
        clarification = Clarification(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=run.id,
            code=ErrorCode.EXTRACTION_CONFIDENCE_LOW,
            fields=list(confidence.keys()),
            question=_CONFIDENCE_LOW_MESSAGE,
            answer=None,
            status=ClarificationStatus.OPEN,
            created_at=now,
            answered_at=None,
        )
        self._clarifications.save(clarification)
        claim = self._transition_claim(claim, ClaimStatus.NEEDS_CLARIFICATION)
        self._complete_run(
            run, ProcessingRunStatus.NEEDS_CLARIFICATION, attempts, error_code=None
        )
        return ProcessingOutcome(
            claim=claim,
            extractions=[],
            attempts=attempts,
            clarification=ClarificationRequest(
                code=clarification.code,
                message=clarification.question,
                fields=clarification.fields,
            ),
        )

    def _fail_run(
        self,
        run: ProcessingRun,
        error_code: str,
        message: str,
        status_code: int,
        attempts: list[ExtractionAttempt] | None = None,
    ) -> ProcessingOutcome:
        self._complete_run(
            run, ProcessingRunStatus.FAILED, attempts or [], error_code=error_code
        )
        raise ApplicationError(error_code, message, status_code)

    def _save_attempt(
        self,
        run: ProcessingRun,
        attempt_number: int,
        preprocessing: list[str],
        *,
        confidence: dict[str, Decimal],
        extraction_id: UUID | None = None,
        error_code: str | None = None,
    ) -> ExtractionAttempt:
        attempt = ExtractionAttempt(
            attempt=attempt_number,
            processing_run_id=run.id,
            preprocessing=preprocessing,
            confidence=confidence,
            extraction_id=extraction_id,
            error_code=error_code,
            message="Extraction provider returned an invalid result."
            if error_code
            else None,
            created_at=datetime.now(UTC),
        )
        return self._attempts.save(run.claim_id, attempt)

    def _complete_run(
        self,
        run: ProcessingRun,
        status: ProcessingRunStatus,
        attempts: list[ExtractionAttempt],
        *,
        error_code: str | None,
    ) -> None:
        completed_at = datetime.now(UTC)
        duration_ms = None
        if run.started_at is not None:
            duration_ms = int((completed_at - run.started_at).total_seconds() * 1000)
        self._runs.save(
            run.model_copy(
                update={
                    "status": status,
                    "completed_at": completed_at,
                    "error_code": error_code,
                }
            )
        )
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=run.claim_id,
            event_type="processing_run.completed",
            actor_type=ActorType.AGENT,
            safe_payload={
                "run_id": str(run.id),
                "status": str(status),
                "attempt_count": len(attempts),
            },
            processing_run_id=run.id,
            duration_ms=duration_ms,
            retry_count=run.retry_count,
            error_code=error_code,
        )
        logger.info(
            "processing run %s for claim %s completed status=%s",
            run.id,
            run.claim_id,
            status,
        )

    def _transition_claim(self, claim: Claim, target: ClaimStatus) -> Claim:
        apply_transition(ClaimStatus(claim.status), target)
        updated = claim.model_copy(
            update={"status": target, "updated_at": datetime.now(UTC)}
        )
        return self._claims.save(updated)

    def _replay(self, claim_id: UUID, run: ProcessingRun) -> ProcessingOutcome:
        receipts = list(self._receipts.list_for_claim(claim_id))
        extractions = [
            result
            for result in self._extractions.list_for_receipts(
                [receipt.id for receipt in receipts]
            )
            if result.processing_run_id == run.id
        ]
        attempts = [
            attempt
            for attempt in self._attempts.list_for_claim(claim_id)
            if attempt.processing_run_id == run.id
        ]
        clarification: ClarificationRequest | None = None
        if run.status == ProcessingRunStatus.NEEDS_CLARIFICATION:
            stored = self._clarifications.latest_for_claim(claim_id)
            if stored is not None and stored.processing_run_id == run.id:
                clarification = ClarificationRequest(
                    code=stored.code,
                    message=stored.question,
                    fields=stored.fields,
                )
        findings = [
            finding
            for finding in self._findings.list_for_claim(claim_id)
            if finding.processing_run_id == run.id
        ]
        evaluations = [
            evaluation
            for evaluation in self._evaluations.list_for_claim(claim_id)
            if evaluation.processing_run_id == run.id
        ]
        decisions = [
            item
            for item in self._decisions.list_for_claim(claim_id)
            if item.processing_run_id == run.id
        ]
        return ProcessingOutcome(
            claim=self._claims.get(claim_id),
            extractions=extractions,
            attempts=attempts,
            clarification=clarification,
            validation_findings=findings,
            policy_evaluations=evaluations,
            decision=decisions[-1] if decisions else None,
        )


def _as_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _min_confidence_map(results: list[ExtractionResult]) -> dict[str, Decimal]:
    """Aggregate per-field confidence across ALL receipts, not just the last."""
    if not results:
        return {}
    return {
        field: min(getattr(result, field).confidence for result in results)
        for field in _CONFIDENCE_FIELDS
    }
