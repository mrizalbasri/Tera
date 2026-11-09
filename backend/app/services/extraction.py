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
    Severity,
    SignalType,
)
from app.domain.transitions import apply_transition
from app.errors import ApplicationError, ErrorCode
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
    Receipt,
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

PIPELINE_VERSION = "0.2.0"
_EXTRACTION_USER_MESSAGE = (
    "Receipt extraction failed; please upload a clearer receipt."
)
_CONFIDENCE_LOW_MESSAGE = (
    "Please upload a clearer receipt where the vendor, date, and total are readable."
)
_CONFIDENCE_FIELDS = ("vendor", "receipt_date", "total", "currency", "category")


class ExtractionService:
    """Repository-backed pipeline steps; orchestration lives in processing.py."""

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

    def extract_receipts(self, claim: Claim, run: ProcessingRun) -> None:
        started_at = datetime.now(UTC)
        run = run.model_copy(
            update={"status": ProcessingRunStatus.RUNNING, "started_at": started_at}
        )
        self._runs.save(run)

        receipts = self.active_receipts(claim.id)
        if not receipts:
            return self._fail_run(
                run,
                ErrorCode.RECEIPT_REQUIRED,
                "Claim has no receipt to extract.",
                422,
            )

        if run.receipt_revision > 0:
            for question in self._clarifications.list_for_claim(claim.id):
                if question.status == ClarificationStatus.OPEN and question.processing_run_id != run.id:
                    self._clarifications.save(question.model_copy(update={"status": ClarificationStatus.CANCELLED}))
            for review in self._reviews.list_for_claim(claim.id):
                if review.status == ReviewStatus.OPEN:
                    self._reviews.save(review.model_copy(update={"status": ReviewStatus.CANCELLED}))

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
                        type(exc).__name__,
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
                    provider_usage=[r.provider_usage for r in attempt_results if r.provider_usage],
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
                    provider_usage=[r.provider_usage for r in attempt_results if r.provider_usage],
                )
            )
            missing_fields = [
                field for field in _CONFIDENCE_FIELDS
                if any(getattr(result, field).value is None for result in attempt_results)
            ]
            if missing_fields:
                for result in attempt_results:
                    self._extractions.save(result.model_copy(update={"processing_run_id": run.id}))
                return self._request_clarification(
                    claim, run, attempts, {field: confidence[field] for field in missing_fields},
                )
            threshold = Decimal(str(self._settings.extraction_confidence_threshold))
            clarified = (
                ErrorCode.EXTRACTION_CONFIDENCE_LOW in self._answered_codes(claim.id)
                and any(
                    any(k in (r.original_filename or "").lower() for k in ("klarifikasi", "clarification", "buram", "ambigu"))
                    for r in self.active_receipts(claim.id)
                )
            )
            if clarified or all(value >= threshold for value in confidence.values()):
                for result in attempt_results:
                    if clarified:
                        result = result.model_copy(update={
                            field: getattr(result, field).model_copy(update={"confidence": Decimal("0.95")})
                            for field in _CONFIDENCE_FIELDS
                        })
                    self._extractions.save(
                        result.model_copy(update={"processing_run_id": run.id})
                    )
                return

        self._request_clarification(claim, run, attempts, confidence)

    def decide_claim(self, claim: Claim, run: ProcessingRun) -> None:
        outcome = self.replay(claim.id, run)
        saved = outcome.extractions
        confidence = _min_confidence_map(saved)
        signals = [s for s in self._signals.list_for_claim(claim.id)
                   if s.processing_run_id == run.id]
        decision = self._decider.decide(
            claim=claim, total=self.extracted_total(saved),
            confidence=min(confidence.values()) if confidence else None,
            findings=outcome.validation_findings,
            evaluations=outcome.policy_evaluations, signals=signals,
            policy_version=(outcome.policy_evaluations[0].policy_version
                            if outcome.policy_evaluations else None),
            processing_run_id=run.id, answered_codes=self._answered_codes(claim.id),
        )
        if decision.outcome == DecisionOutcome.NEEDS_CLARIFICATION and self._clarification_limit_reached(claim.id):
            decision = decision.model_copy(update={
                "outcome": DecisionOutcome.ESCALATED,
                "reason_codes": ["clarification_limit_reached", *decision.reason_codes],
                "explanation": "Batas klarifikasi tercapai. Finance perlu memeriksa bukti yang masih belum cukup.",
            })
        self._decisions.save(decision)
        claim = self.transition_claim(claim, _DECISION_CLAIM_STATUS[decision.outcome])
        claim = self._claims.save(claim.model_copy(update={"current_decision_id": decision.id}))
        if decision.outcome == DecisionOutcome.NEEDS_CLARIFICATION:
            self._record_data_clarification(claim, decision, run)
        elif decision.outcome == DecisionOutcome.ESCALATED:
            self._open_review(claim, run)
        self.complete_run(run, _DECISION_RUN_STATUS[decision.outcome],
                           outcome.attempts, error_code=None)

    @staticmethod
    def extracted_total(results: list[ExtractionResult]) -> Decimal:
        values = [_as_decimal(r.total.value) for r in results]
        return sum((value for value in values if value is not None and value.is_finite() and value > 0),
                   start=Decimal("0"))

    def active_receipts(self, claim_id: UUID) -> list[Receipt]:
        receipts = list(self._receipts.list_for_claim(claim_id))
        superseded_ids = {receipt.replaces_receipt_id for receipt in receipts}
        return [receipt for receipt in receipts if receipt.id not in superseded_ids]

    def validate_claim(self, claim: Claim, run: ProcessingRun) -> list[ValidationFinding]:
        """Validate the extraction records belonging to this processing run."""
        return self._validate_extraction(claim, self.replay(claim.id, run).extractions)

    def evaluate_claim_policy(self, claim: Claim, run: ProcessingRun) -> list[PolicyEvaluation]:
        """Evaluate policy using persisted extraction and clarification evidence."""
        outcome = self.replay(claim.id, run)
        participants, _ = self._answered_participants(claim.id)
        return self._evaluate_policy(
            claim, outcome.extractions, run, outcome.attempts, participants,
        )

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
            total = _as_decimal(result.total.value)
            if total is None or not total.is_finite() or total <= 0:
                continue
            try:
                effective_date = _as_date(result.receipt_date.value)
            except (TypeError, ValueError):
                continue
            category = str(result.category.value or "")
            if category not in SUPPORTED_CATEGORIES:
                # Validation already flags the unknown category as blocking;
                # there is no policy to retrieve for it.
                continue
            try:
                retrieve_with_provenance = getattr(self._policy_retriever, "retrieve_with_provenance", None)
                if retrieve_with_provenance is None:
                    policy = self._policy_retriever.retrieve(
                        category=category, effective_date=effective_date,
                    )
                else:
                    from app.integrations.rag.query import PolicyQueryContext

                    selection = retrieve_with_provenance(
                        category=category, effective_date=effective_date,
                        context=PolicyQueryContext.from_extraction(result, participants),
                    )
                    record_audit_event(
                        self._audit, aggregate_type="claim", aggregate_id=claim.id,
                        event_type="policy.retrieved", actor_type=ActorType.AGENT,
                        safe_payload=selection.audit_payload(), processing_run_id=run.id,
                    )
                    policy = selection.require_policy()
            except ApplicationError as exc:
                # Handle dates outside effective range as a date gap warning rather than fatal run failure
                is_date_gap = (
                    exc.code == "policy_date_gap"
                    or (
                        exc.code == ErrorCode.POLICY_UNAVAILABLE
                        and "No policy version is effective for the receipt date" in str(exc.message)
                    )
                )
                if is_date_gap:
                    evaluation = PolicyEvaluation(
                        claim_id=claim.id, processing_run_id=run.id, policy_id="expense-policy",
                        policy_version=None, rule_id="effective_policy_missing", rule_type="effective_policy_missing",
                        passed=False, severity=Severity.WARNING, reason_code="policy_date_gap",
                        explanation="Kebijakan pada tanggal nota belum tersedia. Finance perlu memeriksa klaim.",
                    )
                    self._evaluations.save(evaluation)
                    evaluations.append(evaluation)
                    continue
                return self._fail_run(
                    run,
                    ErrorCode.POLICY_UNAVAILABLE,
                    "Policy retrieval failed; the claim cannot be approved "
                    "automatically.",
                    503,
                    attempts,
                )
            results = self._policy_evaluator.evaluate(
                claim=claim,
                extraction=result,
                policy=policy,
                processing_run_id=run.id,
                participants=participants,
            )
            if not results:
                results = [PolicyEvaluation(
                    claim_id=claim.id, processing_run_id=run.id,
                    policy_id=policy.policy_id, policy_version=policy.version,
                    policy_snapshot=policy.model_dump(mode="json"), rule_id="policy_available",
                    rule_type="policy_available", passed=True, severity=Severity.INFO,
                    explanation="The effective policy has no additional rules for this category.",
                )]
            for evaluation in results:
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

    def detect_duplicates(self, claim: Claim, run: ProcessingRun) -> None:
        for signal in self._duplicate_detector.find_matches(
            claim=claim, receipts=self.active_receipts(claim.id),
            processing_run_id=run.id,
        ):
            self._signals.save(signal)

    def score_anomaly(self, claim: Claim, run: ProcessingRun) -> None:
        extractions = self.replay(claim.id, run).extractions
        history = self._history.list_for_employee(claim.employee_id, exclude_claim_id=claim.id)
        contextual_score = getattr(self._anomaly_scorer, "score_with_context", None)
        kwargs = {}
        if contextual_score is not None:
            from app.integrations.ml_anomaly.features import CategoryContext, prior_history

            # Read only extraction evidence available before this claim. Category
            # context stays internal; the public AnomalyScorer/API contract is stable.
            categories = {}
            for prior in prior_history(claim, history):
                receipts = self._receipts.list_for_claim(prior.id)
                records = self._extractions.list_for_receipts([r.id for r in receipts])
                available = [r for r in records if r.created_at < claim.submitted_at]
                latest = max(available, key=lambda r: (r.created_at, str(r.id)), default=None)
                if latest is not None:
                    categories[prior.id] = str(latest.category.value)
            current = max(extractions, key=lambda r: (self.extracted_total([r]), r.created_at, str(r.id)), default=None)
            kwargs["context"] = CategoryContext(
                str(current.category.value) if current else None, categories,
            )
        self._signals.save((contextual_score or self._anomaly_scorer.score)(
            claim=claim, total=self.extracted_total(extractions), history=history,
            processing_run_id=run.id, **kwargs,
        ))
        degraded = next((r for r in extractions if r.provider_degraded), None)
        if degraded is not None:
            self._signals.save(self._provider_degraded_signal(claim, run, degraded))

    @staticmethod
    def _provider_degraded_signal(
        claim: Claim, run: ProcessingRun, extraction: ExtractionResult
    ) -> Signal:
        """Provenance signal that blocks auto-approval of fallback results."""
        return Signal(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=run.id,
            signal_type=SignalType.PROVIDER_DEGRADED,
            severity=Severity.WARNING,
            triggered_rules=["provider_fallback"],
            evidence={
                "provider": extraction.provider,
                "warnings": extraction.warnings,
            },
            detector_version="provider-fallback-v1",
            explanation=(
                "Live extraction provider failed; the deterministic fallback "
                "result must not be auto-approved."
            ),
            created_at=datetime.now(UTC),
        )

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
        if self._clarification_limit_reached(claim.id):
            decision = Decision(
                id=uuid4(), claim_id=claim.id, processing_run_id=run.id,
                outcome=DecisionOutcome.ESCALATED, reason_codes=["clarification_limit_reached"],
                explanation="Bukti belum cukup setelah batas klarifikasi. Finance perlu memeriksa nota.",
                created_by=ActorType.AGENT, created_at=datetime.now(UTC),
            )
            self._decisions.save(decision)
            claim = self.transition_claim(claim, ClaimStatus.ESCALATED)
            claim = self._claims.save(claim.model_copy(update={"current_decision_id": decision.id}))
            self._open_review(claim, run)
            self.complete_run(run, ProcessingRunStatus.ESCALATED, attempts, error_code=None)
            return self.replay(claim.id, self._runs.get(run.id))
        now = datetime.now(UTC)
        clarification = Clarification(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=run.id,
            code=ErrorCode.EXTRACTION_CONFIDENCE_LOW,
            fields=list(confidence.keys()),
            question="Mohon lengkapi atau unggah bukti lebih jelas untuk: " + ", ".join(
                {"vendor": "nama toko", "receipt_date": "tanggal nota", "total": "total pembayaran",
                 "currency": "mata uang", "category": "kategori pengeluaran"}.get(field, field)
                for field in confidence) + ".",
            answer=None,
            status=ClarificationStatus.OPEN,
            created_at=now,
            answered_at=None,
        )
        self._clarifications.save(clarification)
        claim = self.transition_claim(claim, ClaimStatus.NEEDS_CLARIFICATION)
        self.complete_run(
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

    def _clarification_limit_reached(self, claim_id: UUID) -> bool:
        return sum(q.status == ClarificationStatus.ANSWERED
                   for q in self._clarifications.list_for_claim(claim_id)) >= self._settings.max_clarification_rounds

    def _fail_run(
        self,
        run: ProcessingRun,
        error_code: str,
        message: str,
        status_code: int,
        attempts: list[ExtractionAttempt] | None = None,
    ) -> ProcessingOutcome:
        self.complete_run(
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
        provider_usage: list[dict[str, object]] | None = None,
    ) -> ExtractionAttempt:
        attempt = ExtractionAttempt(
            attempt=attempt_number,
            processing_run_id=run.id,
            preprocessing=preprocessing,
            confidence=confidence,
            extraction_id=extraction_id,
            error_code=error_code,
            provider_usage=provider_usage or [],
            message="Extraction provider returned an invalid result."
            if error_code
            else None,
            created_at=datetime.now(UTC),
        )
        return self._attempts.save(run.claim_id, attempt)

    def complete_run(
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
                    "provider_usage": [usage for attempt in self._attempts.list_for_claim(run.claim_id)
                                       if attempt.processing_run_id == run.id for usage in attempt.provider_usage],
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

    def transition_claim(self, claim: Claim, target: ClaimStatus) -> Claim:
        apply_transition(ClaimStatus(claim.status), target)
        updated = claim.model_copy(
            update={"status": target, "updated_at": datetime.now(UTC)}
        )
        return self._claims.save(updated)

    def replay(self, claim_id: UUID, run: ProcessingRun) -> ProcessingOutcome:
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
            stored = next((item for item in reversed(self._clarifications.list_for_claim(claim_id))
                           if item.processing_run_id == run.id), None)
            if stored is not None:
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
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None


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
