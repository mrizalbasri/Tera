"""LangChain-backed receipt extraction for live mode (M7, ADR 0002).

Design invariants (spec M7 + FR-13):

- Masking runs HERE, before any prompt leaves the boundary — proven by tests
  that capture the outgoing payload.
- Model output must satisfy the extraction schema; anything else is a
  classified non-retryable error, never a success-shaped fallback.
- Timeouts and rate limits are retryable (bounded, with backoff); malformed
  output and unsupported media are not.
- With PROVIDER_FALLBACK=mock, any live failure degrades to the deterministic
  mock extractor; the result's provider metadata marks the fallback so it is
  always auditable.
"""

import base64
import logging
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.domain.enums import ErrorClassification
from app.errors import ApplicationError, ErrorCode
from app.integrations.masking import SensitiveDataMasker
from app.integrations.mock import MockReceiptExtractor
from app.schemas.core import (
    ExtractedLineItem,
    ExtractionResult,
    FieldConfidence,
    Receipt,
)

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = (
    "You are an expense receipt parser. Extract the vendor, receipt date, "
    "total, currency, and category from this receipt image. Category must be "
    "one of: meals, fuel, toll_parking, hotel, other. Give every field the "
    "same confidence between 0 and 1. Respond only with the required fields."
)

_IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png"}
_FALLBACK_PROVIDER_PREFIX = "llm-fallback-mock"


class LlmExtractionOutput(BaseModel):
    """The structured contract the vision model must return."""

    vendor: str = Field(min_length=1, max_length=255)
    receipt_date: str
    total: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    category: str
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    confidence: Decimal = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class LlmReceiptExtractor:
    """Live ReceiptExtractor implementation via LangChain structured output."""

    provider_name = "llm"

    def __init__(
        self,
        settings: Settings,
        masker: SensitiveDataMasker,
        model: ChatOpenAI | None = None,
    ) -> None:
        self._settings = settings
        self._masker = masker
        self._model = model or ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
            temperature=0,
        )
        self._structured = self._model.with_structured_output(
            LlmExtractionOutput, method="json_mode"
        )
        self._mock = MockReceiptExtractor()

    def extract(
        self,
        *,
        receipt: Receipt,
        content: bytes,
        declared_amount: Decimal | None,
        attempt: int,
    ) -> ExtractionResult:
        try:
            output = self._invoke_structured(receipt, content, declared_amount, attempt)
        except ApplicationError as exc:
            if self._settings.provider_fallback == "mock":
                logger.warning(
                    "live extraction failed (%s); degrading to mock extractor",
                    exc.code,
                )
                return self.fallback_extract(
                    receipt=receipt,
                    content=content,
                    declared_amount=declared_amount,
                    attempt=attempt,
                )
            raise
        return self._to_extraction_result(receipt, output, attempt)

    def fallback_extract(
        self,
        *,
        receipt: Receipt,
        content: bytes,
        declared_amount: Decimal | None,
        attempt: int,
    ) -> ExtractionResult:
        """Deterministic mock fallback; provider metadata marks the degrade."""
        result = self._mock.extract(
            receipt=receipt,
            content=content,
            declared_amount=declared_amount,
            attempt=attempt,
        )
        return result.model_copy(
            update={
                "provider": f"{_FALLBACK_PROVIDER_PREFIX}:{attempt}",
                "warnings": [*result.warnings, "live_provider_unavailable"],
            }
        )

    def _invoke_structured(
        self,
        receipt: Receipt,
        content: bytes,
        declared_amount: Decimal | None,
        attempt: int,
    ) -> LlmExtractionOutput:
        if receipt.media_type not in _IMAGE_MEDIA_TYPES:
            raise self._classified_error(
                "unsupported_media_for_vision",
                ErrorClassification.NON_RETRYABLE,
                f"Live extraction supports JPG and PNG receipts, got "
                f"{receipt.media_type}.",
                415,
            )
        message = self._build_message(receipt, content, declared_amount)
        last_error: ApplicationError | None = None
        for retry in range(self._settings.llm_max_retries + 1):
            try:
                raw = self._structured.invoke([message])
                if isinstance(raw, LlmExtractionOutput):
                    return raw
                if isinstance(raw, BaseModel):
                    return LlmExtractionOutput.model_validate(
                        raw.model_dump(mode="json")
                    )
                return LlmExtractionOutput.model_validate(raw)
            except ValidationError as exc:
                raise self._classified_error(
                    ErrorCode.MALFORMED_EXTRACTION,
                    ErrorClassification.NON_RETRYABLE,
                    "Live extraction returned malformed output.",
                    502,
                    {"detail": str(exc)[:200]},
                ) from exc
            except ApplicationError:
                raise
            except Exception as exc:  # network, timeout, rate limit
                last_error = self._classified_error(
                    "provider_unavailable",
                    ErrorClassification.RETRYABLE,
                    "Extraction provider is unavailable.",
                    503,
                    {"attempt": attempt, "retry": retry},
                )
                logger.warning(
                    "live extraction provider error attempt=%s retry=%s: %s",
                    attempt,
                    retry,
                    exc,
                )
                if retry < self._settings.llm_max_retries:
                    time.sleep(0.2 * (retry + 1))
        assert last_error is not None
        raise last_error

    def _build_message(
        self, receipt: Receipt, content: bytes, declared_amount: Decimal | None
    ) -> HumanMessage:
        # FR-13 choke point: sensitive text fields are masked here, before
        # the prompt leaves the process. The receipt image itself is the
        # submitted source document and must be seen by the vision model.
        prompt = _EXTRACTION_PROMPT
        if declared_amount is not None:
            masked_amount = self._masker.mask(str(declared_amount)).masked_text
            prompt += (
                "\nDeclared amount submitted by the employee: " + masked_amount
            )
        data_uri = (
            f"data:{receipt.media_type};base64,{base64.b64encode(content).decode()}"
        )
        return HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]
        )

    def _to_extraction_result(
        self,
        receipt: Receipt,
        output: LlmExtractionOutput,
        attempt: int,
    ) -> ExtractionResult:
        try:
            receipt_date = date.fromisoformat(output.receipt_date)
        except ValueError as exc:
            raise self._classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction returned a malformed receipt date.",
                502,
            ) from exc
        total = output.total
        return ExtractionResult(
            id=uuid4(),
            receipt_id=receipt.id,
            vendor=FieldConfidence(value=output.vendor, confidence=output.confidence),
            receipt_date=FieldConfidence(
                value=receipt_date, confidence=output.confidence
            ),
            total=FieldConfidence(value=total, confidence=output.confidence),
            currency=FieldConfidence(
                value=output.currency.upper(), confidence=output.confidence
            ),
            category=FieldConfidence(
                value=output.category, confidence=output.confidence
            ),
            line_items=[
                ExtractedLineItem(
                    description=output.vendor,
                    quantity=output.quantity,
                    unit_price=(total / output.quantity).quantize(Decimal("0.01")),
                    total=total,
                )
            ],
            warnings=list(output.warnings),
            provider=(
                f"{self.provider_name}:{self._settings.llm_model}:attempt-{attempt}"
            ),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _classified_error(
        code: str,
        classification: ErrorClassification,
        message: str,
        status_code: int,
        details: dict | None = None,
    ) -> ApplicationError:
        merged = {"classification": str(classification), **(details or {})}
        return ApplicationError(code, message, status_code, merged)
