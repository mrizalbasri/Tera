"""Outbound prompt construction at the privacy boundary (M7, FR-13).

Owns everything about the prompt that leaves the process: the strict image
privacy gate, text masking, image envelope sanitization, and the multimodal
message shape. ``LlmReceiptExtractor`` delegates here so the extractor class
only orchestrates invocation, retry, fallback, and result mapping.

FR-13 choke point: sensitive text fields are masked and the receipt image's
metadata envelope is stripped HERE, before anything leaves the process. The
receipt image itself is the submitted source document and must be seen by
the vision model; parsing failures fail closed rather than send unsanitized
bytes. In strict privacy mode nothing about the image crosses at all.
"""

import base64
from decimal import Decimal

from langchain_core.messages import HumanMessage

from app.config import Settings
from app.domain.enums import ErrorClassification
from app.errors import ErrorCode, classified_error
from app.integrations.image_privacy import strip_image_metadata
from app.integrations.masking import SensitiveDataMasker
from app.schemas.core import Receipt

_EXTRACTION_PROMPT = (
    "You are an expense receipt parser. Extract the vendor, receipt date, "
    "total, currency, and category from this receipt image. Category must be "
    "one of: meals, fuel, toll_parking, hotel, other. Give every field the "
    "same confidence between 0 and 1. Return only a valid JSON object, without "
    "Markdown or extra text, using these fields and types: "
    "vendor: non-empty string (maximum 255 characters); "
    "receipt_date: string in YYYY-MM-DD format; total: positive number; "
    "currency: three-letter currency string; category: string from the list above; "
    "quantity: positive number (use 1 if unspecified); "
    "confidence: number between 0 and 1; warnings: array of strings "
    "(use an empty array if there are no warnings)."
)


def build_extraction_message(
    settings: Settings,
    masker: SensitiveDataMasker,
    receipt: Receipt,
    content: bytes,
    declared_amount: Decimal | None,
) -> HumanMessage:
    """Build the vision prompt with all FR-13 controls applied."""
    if settings.llm_image_privacy_mode == "block":
        # Pixel content cannot be proven free of personal data without a
        # local OCR pass (deferred), so strict deployments fail closed.
        raise classified_error(
            ErrorCode.IMAGE_PRIVACY_BLOCKED,
            ErrorClassification.NON_RETRYABLE,
            "Receipt image forwarding is disabled by privacy policy.",
            422,
        )
    prompt = _EXTRACTION_PROMPT
    if declared_amount is not None:
        masked_amount = masker.mask(str(declared_amount)).masked_text
        prompt += "\nDeclared amount submitted by the employee: " + masked_amount
    try:
        sanitized = strip_image_metadata(content, receipt.media_type)
    except ValueError as exc:
        # Sanitizer messages are static first-party strings; nothing
        # payload-bearing leaves through details.
        raise classified_error(
            ErrorCode.IMAGE_SANITIZATION_FAILED,
            ErrorClassification.NON_RETRYABLE,
            "Receipt image could not be sanitized before the provider call.",
            422,
            {"exception_type": type(exc).__name__},
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
