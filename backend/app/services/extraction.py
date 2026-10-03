from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.config import Settings
from app.domain.enums import ClaimStatus
from app.errors import ApplicationError, NotFoundError
from app.repositories.memory import InMemoryClaimStore
from app.schemas.core import (
    Claim,
    ClarificationRequest,
    ExtractedLineItem,
    ExtractionAttempt,
    ExtractionResult,
    FieldConfidence,
    Receipt,
)


class MockReceiptExtractor:
    provider_name = "mock"

    def extract(
        self,
        *,
        receipt: Receipt,
        content: bytes,
        declared_amount: Decimal | None,
        attempt: int,
    ) -> ExtractionResult:
        if b"MALFORMED" in content:
            raise ApplicationError(
                "malformed_extraction",
                "Extractor returned malformed output.",
                502,
            )
        low_confidence = (
            b"LOW_CONFIDENCE" in content
            and not (
                b"RETRY_THEN_SUCCESS" in content
                and attempt >= 2
            )
        )
        confidence = Decimal("0.55") if low_confidence else Decimal("0.96")
        total = declared_amount or Decimal("10000")
        now = datetime.now(UTC)
        return ExtractionResult(
            id=uuid4(),
            receipt_id=receipt.id,
            vendor=FieldConfidence(value="Synthetic Vendor", confidence=confidence),
            receipt_date=FieldConfidence(
                value=date.today() - timedelta(days=1),
                confidence=confidence,
            ),
            total=FieldConfidence(value=total, confidence=confidence),
            currency=FieldConfidence(value="IDR", confidence=confidence),
            category=FieldConfidence(value="other", confidence=confidence),
            line_items=[
                ExtractedLineItem(
                    description="Synthetic expense",
                    quantity=Decimal("1"),
                    unit_price=total,
                    total=total,
                )
            ],
            warnings=["low_confidence_fixture"] if low_confidence else [],
            provider=f"{self.provider_name}-attempt-{attempt}",
            created_at=now,
        )


class ExtractionService:
    def __init__(
        self,
        store: InMemoryClaimStore,
        settings: Settings,
        extractor: MockReceiptExtractor | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._extractor = extractor or MockReceiptExtractor()

    def process_claim(self, claim_id: UUID) -> dict[str, object]:
        claim = self._store.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))
        cached_result = self._store.get_processing_result(claim_id)
        if cached_result is not None:
            return cached_result
        receipts = list(self._store.list_receipts(claim_id))
        if not receipts:
            raise ApplicationError(
                "receipt_required",
                "Claim has no receipt to extract.",
                422,
            )

        attempts: list[ExtractionAttempt] = []
        results: list[ExtractionResult] = []
        clarification: ClarificationRequest | None = None
        for attempt_number in range(1, self._settings.max_processing_retries + 2):
            preprocessing = ["normalize_document"] if attempt_number > 1 else []
            attempt_results: list[ExtractionResult] = []
            errors: list[str] = []
            for receipt in receipts:
                content = self._store.get_content(receipt.storage_reference)
                if content is None:
                    errors.append("receipt_content_unavailable")
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
                attempt_results.append(result)

            if errors:
                attempt = ExtractionAttempt(
                    attempt=attempt_number,
                    preprocessing=preprocessing,
                    confidence={},
                    error_code=errors[0],
                    message="Extraction provider returned an invalid result.",
                    created_at=datetime.now(UTC),
                )
                self._store.save_attempt(claim_id, attempt)
                attempts.append(attempt)
                raise ApplicationError(
                    errors[0],
                    "Receipt extraction failed; please upload a clearer receipt.",
                    502,
                )

            confidence = _confidence_map(attempt_results)
            attempt = ExtractionAttempt(
                attempt=attempt_number,
                preprocessing=preprocessing,
                confidence=confidence,
                extraction_id=attempt_results[0].id if attempt_results else None,
                created_at=datetime.now(UTC),
            )
            self._store.save_attempt(claim_id, attempt)
            attempts.append(attempt)
            results.extend(attempt_results)
            if all(
                value >= Decimal(str(self._settings.extraction_confidence_threshold))
                for value in confidence.values()
            ):
                for result in attempt_results:
                    self._store.save_extraction(result)
                response = {
                    "claim": claim,
                    "extractions": results,
                    "attempts": attempts,
                    "clarification": None,
                }
                self._store.save_processing_result(claim_id, response)
                return response

        clarification = ClarificationRequest(
            code="extraction_confidence_low",
            message="Please upload a clearer receipt where the vendor, date, and total are readable.",
            fields=list(_confidence_map(results).keys()),
        )
        updated_claim = claim.model_copy(
            update={
                "status": ClaimStatus.NEEDS_CLARIFICATION,
                "updated_at": datetime.now(UTC),
            }
        )
        self._store.save_claim(updated_claim)
        response = {
            "claim": updated_claim,
            "extractions": results,
            "attempts": attempts,
            "clarification": clarification,
        }
        self._store.save_processing_result(claim_id, response)
        return response


def _confidence_map(results: list[ExtractionResult]) -> dict[str, Decimal]:
    if not results:
        return {}
    result = results[-1]
    return {
        "vendor": result.vendor.confidence,
        "receipt_date": result.receipt_date.confidence,
        "total": result.total.confidence,
        "currency": result.currency.confidence,
        "category": result.category.confidence,
    }
