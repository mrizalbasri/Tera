"""Deterministic mock extractor used until a real OCR/LLM provider is wired.

Fixture markers inside the receipt content steer behavior in tests:

- ``MALFORMED``: provider failure (classified as non-retryable).
- ``LOW_CONFIDENCE``: all fields come back below the confidence threshold.
- ``RETRY_THEN_SUCCESS``: from the second attempt on, confidence is high.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.errors import ApplicationError, ErrorCode
from app.schemas.core import (
    ExtractedLineItem,
    ExtractionResult,
    FieldConfidence,
    Receipt,
)

LOW_CONFIDENCE_SCORE = Decimal("0.55")
HIGH_CONFIDENCE_SCORE = Decimal("0.96")


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
                ErrorCode.MALFORMED_EXTRACTION,
                "Extractor returned malformed output.",
                502,
            )
        low_confidence = b"LOW_CONFIDENCE" in content and not (
            b"RETRY_THEN_SUCCESS" in content and attempt >= 2
        )
        confidence = LOW_CONFIDENCE_SCORE if low_confidence else HIGH_CONFIDENCE_SCORE
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
