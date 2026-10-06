from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable error codes shared by services and the API error contract."""

    INVALID_CLAIM = "invalid_claim"
    INVALID_FILE = "invalid_file"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    FILE_TOO_LARGE = "file_too_large"
    RECEIPT_REQUIRED = "receipt_required"
    DUPLICATE_RECEIPT = "duplicate_receipt"
    MALFORMED_EXTRACTION = "malformed_extraction"
    IMAGE_SANITIZATION_FAILED = "image_sanitization_failed"
    RECEIPT_CONTENT_UNAVAILABLE = "receipt_content_unavailable"
    EXTRACTION_CONFIDENCE_LOW = "extraction_confidence_low"
    POLICY_UNAVAILABLE = "policy_unavailable"
    PERSISTENCE_CONFLICT = "persistence_conflict"
    IDEMPOTENCY_IN_PROGRESS = "idempotency_in_progress"
    NOT_FOUND = "not_found"
    INVALID_STATE_TRANSITION = "invalid_state_transition"


@dataclass(frozen=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(ApplicationError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} '{identifier}' was not found.",
            status_code=404,
        )


class InvalidStateTransitionError(ApplicationError):
    def __init__(self, resource: str, current: str, target: str) -> None:
        super().__init__(
            code=ErrorCode.INVALID_STATE_TRANSITION,
            message=f"{resource} cannot transition from '{current}' to '{target}'.",
            status_code=409,
        )
