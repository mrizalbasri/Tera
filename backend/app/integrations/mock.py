"""Deterministic mock extractor used until a real OCR/LLM provider is wired.

Fixture markers inside the receipt content steer behavior in tests:

- ``MALFORMED``: provider failure (classified as non-retryable).
- ``LOW_CONFIDENCE``: all fields come back below the confidence threshold.
- ``RETRY_THEN_SUCCESS``: from the second attempt on, confidence is high.
- ``CATEGORY:MEALS|FUEL|TOLL|HOTEL``: sets the extracted category.
- ``TOTAL_MISMATCH``: line item sum disagrees with the extracted total.
- ``ALCOHOL``: adds a prohibited item to the line items.
- ``OLD_DATE`` / ``FUTURE_DATE``: receipt date 20 days old / tomorrow.
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

_CATEGORY_MARKERS = {
    b"CATEGORY:MEALS": "meals",
    b"CATEGORY:FUEL": "fuel",
    b"CATEGORY:TOLL": "toll_parking",
    b"CATEGORY:HOTEL": "hotel",
}


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
        category = next(
            (
                value
                for marker, value in _CATEGORY_MARKERS.items()
                if marker in content
            ),
            "other",
        )
        receipt_date = date.today() - timedelta(days=1)
        if b"OLD_DATE" in content:
            receipt_date = date.today() - timedelta(days=20)
        elif b"FUTURE_DATE" in content:
            receipt_date = date.today() + timedelta(days=1)
        line_total = total / 2 if b"TOTAL_MISMATCH" in content else total
        description = (
            "Synthetic alcohol beer" if b"ALCOHOL" in content else "Synthetic expense"
        )
        now = datetime.now(UTC)
        return ExtractionResult(
            id=uuid4(),
            receipt_id=receipt.id,
            vendor=FieldConfidence(value="Synthetic Vendor", confidence=confidence),
            receipt_date=FieldConfidence(
                value=receipt_date,
                confidence=confidence,
            ),
            total=FieldConfidence(value=total, confidence=confidence),
            currency=FieldConfidence(value="IDR", confidence=confidence),
            category=FieldConfidence(value=category, confidence=confidence),
            line_items=[
                ExtractedLineItem(
                    description=description,
                    quantity=Decimal("1"),
                    unit_price=line_total,
                    total=line_total,
                )
            ],
            warnings=["low_confidence_fixture"] if low_confidence else [],
            provider=f"{self.provider_name}-attempt-{attempt}",
            created_at=now,
        )
