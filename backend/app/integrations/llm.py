"""LangChain-backed receipt extraction for live mode (M7, ADR 0002).

Design invariants (spec M7 + FR-13):

- Masking runs HERE, before any prompt leaves the boundary — proven by tests
  that capture the outgoing payload. The receipt image itself is the source
  document the vision model must see, so its pixels cannot be masked; instead
  the image envelope (EXIF/XMP/IPTC/comments) is stripped here, image bytes
  are never logged or persisted beyond the receipt's own storage reference,
  and `LLM_IMAGE_PRIVACY_MODE=block` fails closed entirely (routing to the
  local mock) for deployments that cannot accept pixel disclosure.
- Model output must satisfy the extraction schema; anything else is a
  classified non-retryable error, never a success-shaped fallback.
- Timeouts and rate limits are retryable (bounded, with backoff); malformed
  output and unsupported media are not.
- With PROVIDER_FALLBACK=mock, transient provider failures — and only the
  documented unsupported-media case — degrade to the deterministic mock
  extractor. Malformed output, sanitization failures, and configuration
  errors always surface: the mock must never turn a contract or privacy
  violation into a success-shaped result. The fallback result's provider
  metadata marks the degrade so it is always auditable.
"""

import base64
import logging
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import openai
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.domain.enums import ErrorClassification
from app.errors import ApplicationError, ErrorCode
from app.integrations.image_privacy import strip_image_metadata
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

# M7 error taxonomy for provider SDK failures. First match wins —
# APITimeoutError subclasses APIConnectionError, so it must come first.
# Transient transport failures are retryable; anything caused by OUR
# configuration or the request shape is not, because retrying cannot fix it.
_PROVIDER_ERROR_MAP: tuple[
    tuple[tuple[type[Exception], ...], str, str, int, ErrorClassification], ...
] = (
    (
        (openai.APITimeoutError,),
        ErrorCode.PROVIDER_TIMEOUT,
        "Extraction provider timed out.",
        504,
        ErrorClassification.RETRYABLE,
    ),
    (
        (openai.RateLimitError,),
        ErrorCode.PROVIDER_RATE_LIMITED,
        "Extraction provider rate limit was hit.",
        429,
        ErrorClassification.RETRYABLE,
    ),
    (
        (openai.APIConnectionError,),
        ErrorCode.PROVIDER_UNAVAILABLE,
        "Extraction provider is unreachable.",
        503,
        ErrorClassification.RETRYABLE,
    ),
    (
        (openai.AuthenticationError, openai.PermissionDeniedError),
        ErrorCode.PROVIDER_AUTHENTICATION_FAILED,
        "Provider rejected the configured credentials.",
        502,
        ErrorClassification.NON_RETRYABLE,
    ),
    (
        (openai.BadRequestError,),
        ErrorCode.PROVIDER_INVALID_REQUEST,
        "Provider rejected the extraction request.",
        502,
        ErrorClassification.NON_RETRYABLE,
    ),
    (
        (openai.NotFoundError,),
        ErrorCode.PROVIDER_UNSUPPORTED_CONFIGURATION,
        "Provider does not support the configured model or endpoint.",
        502,
        ErrorClassification.NON_RETRYABLE,
    ),
)


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
            if (
                self._settings.provider_fallback == "mock"
                and self._fallback_allowed(exc)
            ):
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
                "provider_degraded": True,
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
                ErrorCode.UNSUPPORTED_MEDIA_FOR_VISION,
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
            except OutputParserException as exc:
                # LangChain could not parse the model response into the
                # contract — the provider answered, but unusably. That is a
                # malformed-output case: classified, never retried, never
                # hidden behind fallback.
                raise self._classified_error(
                    ErrorCode.MALFORMED_EXTRACTION,
                    ErrorClassification.NON_RETRYABLE,
                    "Live extraction output could not be parsed.",
                    502,
                    {"detail": str(exc)[:200]},
                ) from exc
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
            except Exception as exc:
                error, classification = self._classify_provider_error(exc)
                logger.warning(
                    "live extraction provider error attempt=%s retry=%s: %s: %s",
                    attempt,
                    retry,
                    type(exc).__name__,
                    exc,
                )
                if classification is ErrorClassification.NON_RETRYABLE:
                    raise error
                last_error = error
                if retry < self._settings.llm_max_retries:
                    time.sleep(0.2 * (retry + 1))
        assert last_error is not None
        raise last_error

    def _build_message(
        self, receipt: Receipt, content: bytes, declared_amount: Decimal | None
    ) -> HumanMessage:
        # FR-13 choke point: sensitive text fields are masked here, before
        # the prompt leaves the process. The receipt image itself is the
        # submitted source document and must be seen by the vision model;
        # its metadata envelope is stripped, and parsing failures fail
        # closed rather than send unsanitized bytes. In strict privacy mode
        # nothing about the image crosses the boundary at all.
        if self._settings.llm_image_privacy_mode == "block":
            # Pixel content cannot be proven free of personal data without a
            # local OCR pass (deferred), so strict deployments fail closed.
            raise self._classified_error(
                ErrorCode.IMAGE_PRIVACY_BLOCKED,
                ErrorClassification.NON_RETRYABLE,
                "Receipt image forwarding is disabled by privacy policy.",
                422,
            )
        prompt = _EXTRACTION_PROMPT
        if declared_amount is not None:
            masked_amount = self._masker.mask(str(declared_amount)).masked_text
            prompt += (
                "\nDeclared amount submitted by the employee: " + masked_amount
            )
        try:
            sanitized = strip_image_metadata(content, receipt.media_type)
        except ValueError as exc:
            raise self._classified_error(
                ErrorCode.IMAGE_SANITIZATION_FAILED,
                ErrorClassification.NON_RETRYABLE,
                "Receipt image could not be sanitized before the provider call.",
                422,
                {"reason": str(exc)},
            ) from exc
        data_uri = (
            f"data:{receipt.media_type};base64,{base64.b64encode(sanitized).decode()}"
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
        # Keep enough precision that a tiny total over a huge quantity never
        # rounds the unit price down to zero (the schema requires > 0); a
        # still-degenerate quotient is a contract violation, not a 500.
        quotient = total / output.quantity
        unit_price = quotient.quantize(Decimal("0.01"))
        if unit_price <= 0:
            unit_price = quotient.quantize(Decimal("0.000001"))
        if unit_price <= 0:
            raise self._classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction produced a degenerate line item.",
                502,
                {"total": str(total), "quantity": str(output.quantity)},
            )
        try:
            return ExtractionResult(
                id=uuid4(),
                receipt_id=receipt.id,
                vendor=FieldConfidence(
                    value=output.vendor, confidence=output.confidence
                ),
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
                        unit_price=unit_price,
                        total=total,
                    )
                ],
                warnings=list(output.warnings),
                provider=(
                    f"{self.provider_name}:{self._settings.llm_model}:attempt-{attempt}"
                ),
                created_at=datetime.now(UTC),
            )
        except ValidationError as exc:
            # The structured-output contract passed, but a field violated the
            # ExtractionResult schema (e.g. length limits); that is provider
            # misbehaviour, classified — never an unclassified 500.
            raise self._classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction output violated the result schema.",
                502,
                {"detail": str(exc)[:200]},
            ) from exc

    @classmethod
    def _classify_provider_error(
        cls, exc: Exception
    ) -> tuple[ApplicationError, ErrorClassification]:
        """Map a provider SDK failure onto the M7 error taxonomy.

        Unknown failures stay retryable (bounded): an unclassified transient
        error is safer to re-try than to abandon, while classified
        configuration errors never retry.
        """
        details = {"error_type": type(exc).__name__}
        for types, code, message, status, classification in _PROVIDER_ERROR_MAP:
            if isinstance(exc, types):
                return (
                    cls._classified_error(
                        code, classification, message, status, details
                    ),
                    classification,
                )
        return (
            cls._classified_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                ErrorClassification.RETRYABLE,
                "Extraction provider is unavailable.",
                503,
                details,
            ),
            ErrorClassification.RETRYABLE,
        )

    @staticmethod
    def _fallback_allowed(exc: ApplicationError) -> bool:
        """Decide whether a failed live extraction may degrade to the mock.

        Only transient provider failures and the documented unsupported-media
        case (PDF in live mode) may degrade. Malformed model output, image
        sanitization failures, and credential/request-configuration errors
        must re-raise: retrying the mock cannot fix them, and a fallback
        result would mask a contract or privacy violation as success.

        The one additional allowed case is the strict privacy gate
        (`image_privacy_blocked`): the provider must not receive the image,
        and the mock runs entirely in-process — degrading there is the
        documented routing, not a masked failure.
        """
        if exc.details and exc.details.get("classification") == str(
            ErrorClassification.RETRYABLE
        ):
            return True
        return exc.code in (
            ErrorCode.UNSUPPORTED_MEDIA_FOR_VISION,
            ErrorCode.IMAGE_PRIVACY_BLOCKED,
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
