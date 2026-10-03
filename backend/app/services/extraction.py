import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.audit.events import record_audit_event
from app.config import Settings
from app.domain.enums import ActorType, ClaimStatus, ClarificationStatus, ProcessingRunStatus
from app.domain.transitions import apply_transition
from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    ClarificationRepository,
    ExtractionAttemptRepository,
    ExtractionRepository,
    FileStorage,
    ProcessingRunRepository,
    ReceiptExtractor,
    ReceiptRepository,
)
from app.schemas.core import (
    Clarification,
    ClarificationRequest,
    Claim,
    ExtractionAttempt,
    ExtractionResult,
    ProcessingOutcome,
    ProcessingRun,
)

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
        audit: AuditRepository,
        extractor: ReceiptExtractor,
        settings: Settings,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._storage = storage
        self._runs = runs
        self._extractions = extractions
        self._attempts = attempts
        self._clarifications = clarifications
        self._audit = audit
        self._extractor = extractor
        self._settings = settings

    def process_claim(self, claim_id: UUID) -> ProcessingOutcome:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        latest_run = self._runs.latest_for_claim(claim_id)
        if latest_run is not None and latest_run.status in (
            ProcessingRunStatus.SUCCEEDED,
            ProcessingRunStatus.NEEDS_CLARIFICATION,
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
        elif not (
            current_status is ClaimStatus.PROCESSING
            and latest_run is not None
            and latest_run.status == ProcessingRunStatus.FAILED
        ):
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
                self._complete_run(
                    run, ProcessingRunStatus.SUCCEEDED, attempts, error_code=None
                )
                return ProcessingOutcome(
                    claim=self._claims.get(claim.id) or claim,
                    extractions=saved,
                    attempts=attempts,
                    clarification=None,
                )

        return self._request_clarification(claim, run, attempts, confidence)

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
        return ProcessingOutcome(
            claim=self._claims.get(claim_id),
            extractions=extractions,
            attempts=attempts,
            clarification=clarification,
        )


def _min_confidence_map(results: list[ExtractionResult]) -> dict[str, Decimal]:
    """Aggregate per-field confidence across ALL receipts, not just the last."""
    if not results:
        return {}
    return {
        field: min(getattr(result, field).confidence for result in results)
        for field in _CONFIDENCE_FIELDS
    }
