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

import logging
import re
import time
from datetime import UTC, date, datetime
from decimal import Decimal, DecimalException
from uuid import uuid4

import openai
from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, PrivateAttr, ValidationError, field_validator

from app.config import Settings
from app.domain.enums import ErrorClassification
from app.errors import ApplicationError, ErrorCode, classified_error
from app.integrations.llm_prompt import build_extraction_message, build_text_extraction_message
from app.integrations.masking import SensitiveDataMasker
from app.integrations.mock import MockReceiptExtractor
from app.schemas.core import (
    ExtractedLineItem,
    ExtractionResult,
    FieldConfidence,
    Receipt,
)

logger = logging.getLogger(__name__)

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


class LlmLineItem(BaseModel):
    description: str = Field(min_length=1, max_length=255, pattern=r"\S")
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    total: Decimal = Field(gt=0, max_digits=18, decimal_places=6)

    @field_validator("unit_price", "total", mode="before")
    @classmethod
    def printed_amount(cls, value: object) -> object:
        from app.services.money import receipt_money

        return receipt_money(value)


class LlmExtractionOutput(BaseModel):
    """The structured contract the vision model must return."""

    vendor: str | None = Field(min_length=1, max_length=255)
    receipt_date: str | None
    # Bound magnitude and scale before derived prices or downstream formatting.
    total: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    currency: str = Field(min_length=3, max_length=3)
    category: str
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=18, decimal_places=6)
    confidence: Decimal = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    subtotal: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    tax: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    discount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    total_ambiguous: bool = False
    line_items: list[LlmLineItem] = Field(default_factory=list, max_length=100)
    line_items_complete: bool = Field(default=False, strict=True)
    _provider_usage: dict = PrivateAttr(default_factory=dict)

    @field_validator("total", "subtotal", "tax", "discount", mode="before")
    @classmethod
    def printed_amount(cls, value: object) -> object:
        from app.services.money import receipt_money

        return receipt_money(value)


def _uncertain_fields(warnings: list[str]) -> set[str]:
    field = r"\b(?:vendor|(?:receipt\s+)?date)\b"
    coordinated_fields = rf"{field}(?:\s+(?:and|&)\s+{field})*"
    uncertain = r"\b(?:blur\w*|unread\w*|illegib\w*|estimat\w*|infer\w*|default\w*|placeholder\w*|missing|not (?:found|visible|available))\b"
    fields: set[str] = set()
    for warning in warnings:
        for clause in re.split(r"[,;.!?\n]|\b(?:but|while)\b", warning.replace("_", " ").lower()):
            mentions = list(re.finditer(coordinated_fields, clause))
            boundaries = [0]
            for previous, current in zip(mentions, mentions[1:]):
                gap = clause[previous.end():current.start()]
                connectors = list(re.finditer(r"\band\b|&", gap))
                # In "vendor clear and unreadable date", the adjective after
                # the conjunction belongs to the following field.
                prefix = connectors[-1].end() if connectors else len(gap)
                boundaries.append(previous.end() + prefix if re.search(uncertain, gap[prefix:]) else current.start())
            boundaries.append(len(clause))
            for index, mention in enumerate(mentions):
                start, end = boundaries[index:index + 2]
                if re.search(uncertain, clause[start:end]):
                    for name in re.findall(field, mention.group()):
                        fields.add("vendor" if name == "vendor" else "receipt_date")
    return fields


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

    def extract_text(
        self, *, receipt: Receipt, text: str,
        declared_amount: Decimal | None, attempt: int,
    ) -> ExtractionResult:
        """Interpret readable OCR evidence without paying for a vision request."""
        if self._settings.llm_image_privacy_mode == "block":
            raise classified_error(
                ErrorCode.IMAGE_PRIVACY_BLOCKED, ErrorClassification.NON_RETRYABLE,
                "External receipt fallback is disabled by privacy policy.", 422,
            )
        message = build_text_extraction_message(self._masker, text, declared_amount)
        output = self._invoke_message(message)
        return self._to_extraction_result(receipt, output, attempt, provider_name="ocr-text")

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
            raise classified_error(
                ErrorCode.UNSUPPORTED_MEDIA_FOR_VISION,
                ErrorClassification.NON_RETRYABLE,
                f"Live extraction supports JPG and PNG receipts, got "
                f"{receipt.media_type}.",
                415,
            )
        message = build_extraction_message(
            self._settings, self._masker, receipt, content, declared_amount
        )
        return self._invoke_message(message)

    def _invoke_message(self, message) -> LlmExtractionOutput:
        last_error: ApplicationError | None = None
        for retry in range(self._settings.llm_max_retries + 1):
            try:
                from app.integrations.usage import UsageCapture

                capture = UsageCapture()
                structured = self._structured.with_config(callbacks=[capture]) if hasattr(self._structured, "with_config") else self._structured
                raw = structured.invoke([message])
                if isinstance(raw, BaseModel):
                    output = LlmExtractionOutput.model_validate(
                        raw.model_dump(mode="json")
                    )
                else:
                    output = LlmExtractionOutput.model_validate(raw)
                output._provider_usage = {**capture.usage, "model": self._settings.llm_model}
                return output
            except OutputParserException as exc:
                # LangChain could not parse the model response into the
                # contract — the provider answered, but unusably. That is a
                # malformed-output case: classified, never retried, never
                # hidden behind fallback. Exception text can carry raw model
                # output, so details stay type-only.
                raise classified_error(
                    ErrorCode.MALFORMED_EXTRACTION,
                    ErrorClassification.NON_RETRYABLE,
                    "Live extraction output could not be parsed.",
                    502,
                    {"exception_type": type(exc).__name__},
                ) from exc
            except ValidationError as exc:
                raise classified_error(
                    ErrorCode.MALFORMED_EXTRACTION,
                    ErrorClassification.NON_RETRYABLE,
                    "Live extraction returned malformed output.",
                    502,
                    {"exception_type": type(exc).__name__},
                ) from exc
            except ApplicationError:
                raise
            except Exception as exc:
                error, classification = self._classify_provider_error(exc)
                logger.warning(
                    "live extraction provider error code=%s classification=%s type=%s",
                    error.code,
                    classification,
                    type(exc).__name__,
                )
                if classification is ErrorClassification.NON_RETRYABLE:
                    raise error
                last_error = error
                if retry < self._settings.llm_max_retries:
                    time.sleep(0.2 * (retry + 1))
        assert last_error is not None
        raise last_error

    def _to_extraction_result(
        self,
        receipt: Receipt,
        output: LlmExtractionOutput,
        attempt: int,
        *,
        provider_name: str | None = None,
    ) -> ExtractionResult:
        warnings = list(output.warnings)
        uncertain_fields = _uncertain_fields(warnings)
        try:
            receipt_date = (
                date.fromisoformat(output.receipt_date)
                if output.receipt_date and output.receipt_date.strip() and "receipt_date" not in uncertain_fields
                else None
            )
        except ValueError as exc:
            raise classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction returned a malformed receipt date.",
                502,
            ) from exc
        vendor = output.vendor if "vendor" not in uncertain_fields else None
        if receipt_date is None and "receipt_date_unreadable" not in warnings:
            warnings.append("receipt_date_unreadable")
        if vendor is None and "vendor_unreadable" not in warnings:
            warnings.append("vendor_unreadable")
        total = output.total
        # Keep enough precision that a tiny total over a huge quantity never
        # rounds the unit price down to zero (the schema requires > 0); a
        # still-degenerate quotient is a contract violation, not a 500.
        try:
            quotient = total / output.quantity
            unit_price = quotient.quantize(Decimal("0.01"))
            if unit_price <= 0:
                unit_price = quotient.quantize(Decimal("0.000001"))
        except DecimalException as exc:
            raise classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction returned unsupported numeric values.",
                502,
                {"stage": "line_item_derivation", "exception_type": type(exc).__name__},
            ) from exc
        if unit_price <= 0:
            raise classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction produced a degenerate line item.",
                502,
                {"stage": "line_item_derivation"},
            )
        try:
            return ExtractionResult(
                id=uuid4(),
                receipt_id=receipt.id,
                vendor=FieldConfidence(
                    value=vendor, confidence=output.confidence if vendor is not None else Decimal("0")
                ),
                receipt_date=FieldConfidence(
                    value=receipt_date, confidence=output.confidence if receipt_date is not None else Decimal("0")
                ),
                total=FieldConfidence(value=total, confidence=output.confidence),
                currency=FieldConfidence(
                    value=output.currency.upper(), confidence=output.confidence
                ),
                category=FieldConfidence(
                    value=output.category, confidence=output.confidence
                ),
                line_items=[ExtractedLineItem(**item.model_dump()) for item in output.line_items] or [
                    ExtractedLineItem(
                        description=vendor or "Receipt summary",
                        quantity=output.quantity,
                        unit_price=unit_price,
                        total=total,
                    )
                ],
                warnings=warnings,
                subtotal=output.subtotal,
                tax=output.tax,
                discount=output.discount,
                total_ambiguous=output.total_ambiguous,
                line_items_derived=not bool(output.line_items),
                line_items_complete=bool(output.line_items) and output.line_items_complete,
                provider_usage=output._provider_usage,
                provider=(
                    f"{provider_name or self.provider_name}:{self._settings.llm_model}:attempt-{attempt}"
                ),
                created_at=datetime.now(UTC),
            )
        except ValidationError as exc:
            # The structured-output contract passed, but a field violated the
            # ExtractionResult schema (e.g. length limits); that is provider
            # misbehaviour, classified — never an unclassified 500. Exception
            # text can echo model output, so details stay type-only.
            raise classified_error(
                ErrorCode.MALFORMED_EXTRACTION,
                ErrorClassification.NON_RETRYABLE,
                "Live extraction output violated the result schema.",
                502,
                {"exception_type": type(exc).__name__},
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
                    classified_error(
                        code, classification, message, status, details
                    ),
                    classification,
                )
        return (
            classified_error(
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
