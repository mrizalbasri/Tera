from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import PurePath
import time
from contextlib import nullcontext
from uuid import UUID, uuid4

from app.audit.events import record_audit_event
from app.config import Settings
from app.domain.enums import ActorType, ClaimStatus
from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    FileStorage,
    ReceiptQualityChecker,
    ReceiptRepository,
)
from app.schemas.core import Claim, Receipt

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": {b"\xff\xd8\xff"},
    "image/png": {b"\x89PNG\r\n\x1a\n"},
    "application/pdf": {b"%PDF-"},
}
MAX_FILENAME_LENGTH = 255


@dataclass(frozen=True)
class ReceiptUpload:
    """Transport-independent receipt input after bounded upload reading."""

    filename: str | None
    media_type: str | None
    content: bytes


@dataclass(frozen=True)
class PreparedReceipt:
    filename: str
    media_type: str
    content: bytes
    content_hash: str
    quality_score: float
    quality_findings: list[str]


class IntakeService:
    def __init__(
        self,
        claims: ClaimRepository,
        receipts: ReceiptRepository,
        storage: FileStorage,
        quality: ReceiptQualityChecker,
        audit: AuditRepository,
        settings: Settings,
        resources=None,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._storage = storage
        self._quality = quality
        self._audit = audit
        self._settings = settings
        self._resources = resources

    def create_claim(
        self, *, employee_id: str, currency: str, declared_amount: Decimal | None,
        files: list[ReceiptUpload], idempotency_key: str | None,
    ) -> tuple[Claim, list[Receipt], bool]:
        with self._resources.claim_lock("receipt-intake") if self._resources else nullcontext():
            with self._resources.transaction() if self._resources else nullcontext():
                return self._create_claim(
                    employee_id=employee_id, currency=currency, declared_amount=declared_amount,
                    files=files, idempotency_key=idempotency_key,
                )

    def _create_claim(
        self,
        *,
        employee_id: str,
        currency: str,
        declared_amount: Decimal | None,
        files: list[ReceiptUpload],
        idempotency_key: str | None,
    ) -> tuple[Claim, list[Receipt], bool]:
        employee_id = employee_id.strip()
        currency = currency.strip().upper()
        if not employee_id:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM, "employee_id is required.", 422
            )
        if len(currency) != 3 or not currency.isalpha():
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM, "currency must be a three-letter code.", 422
            )
        if not files:
            raise ApplicationError(
                ErrorCode.RECEIPT_REQUIRED, "At least one receipt is required.", 422
            )
        if len(files) > self._settings.max_receipts_per_claim:
            raise ApplicationError("too_many_receipts", "Too many receipts in one claim.", 422)
        if sum(len(upload.content) for upload in files) > self._settings.max_upload_total_bytes:
            raise ApplicationError("upload_too_large", "Combined receipts exceed the upload limit.", 413)
        if len(employee_id) > 100:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "employee_id exceeds 100 characters.", 422)

        if idempotency_key:
            existing = self._claims.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing, list(self._receipts.list_for_claim(existing.id)), True

        prepared: list[PreparedReceipt] = []
        seen_hashes: set[str] = set()
        for upload in files:
            candidate = self._prepare_receipt(upload, seen_hashes)
            existing_claim_id = self._receipts.find_claim_id_by_content_hash(
                candidate.content_hash
            )
            if existing_claim_id:
                raise ApplicationError(
                    ErrorCode.DUPLICATE_RECEIPT,
                    "A receipt with the same content has already been submitted.",
                    409,
                    {"claim_id": str(existing_claim_id)},
                )
            seen_hashes.add(candidate.content_hash)
            prepared.append(candidate)

        now = datetime.now(UTC)
        claim = Claim(
            id=uuid4(),
            employee_id=employee_id,
            status=ClaimStatus.RECEIVED,
            submitted_at=now,
            currency=currency,
            declared_amount=declared_amount,
            created_at=now,
            updated_at=now,
        )
        if idempotency_key:
            # The reservation is the atomic gate: losing the race means
            # another request with the same key owns this submission.
            if not self._claims.reserve_idempotency_key(idempotency_key, claim.id):
                existing = self._await_claim(idempotency_key)
                if existing is not None:
                    return (
                        existing,
                        list(self._receipts.list_for_claim(existing.id)),
                        True,
                    )
                raise ApplicationError(
                    ErrorCode.IDEMPOTENCY_IN_PROGRESS,
                    "A request with this Idempotency-Key is still in progress.",
                    409,
                )
        self._claims.save(claim)
        receipts: list[Receipt] = []
        for candidate in prepared:
            reference = self._storage.put(
                candidate.content,
                filename=candidate.filename,
                media_type=candidate.media_type,
            )
            receipt = Receipt(
                id=uuid4(),
                claim_id=claim.id,
                original_filename=candidate.filename,
                media_type=candidate.media_type,
                storage_reference=reference,
                content_hash=candidate.content_hash,
                quality_score=Decimal(str(candidate.quality_score)),
                quality_findings=candidate.quality_findings,
                created_at=now,
            )
            self._receipts.save(receipt)
            receipts.append(receipt)
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim.id,
            event_type="claim.received",
            actor_type=ActorType.EMPLOYEE,
            safe_payload={
                "receipt_count": len(receipts),
                "media_types": [receipt.media_type for receipt in receipts],
            },
        )
        return claim, receipts, False

    def _await_claim(self, key: str) -> Claim | None:
        """Wait briefly for an in-flight winner of the same idempotency key."""
        for _ in range(20):
            time.sleep(0.05)
            existing = self._claims.get_by_idempotency_key(key)
            if existing is not None:
                return existing
        return None

    def replace_receipt(self, *, claim_id: UUID, upload: ReceiptUpload) -> tuple[Claim, Receipt]:
        with self._resources.claim_lock(claim_id) if self._resources else nullcontext():
            with self._resources.claim_lock("receipt-intake") if self._resources else nullcontext():
                with self._resources.transaction() if self._resources else nullcontext():
                    return self._replace_receipt(claim_id=claim_id, upload=upload)

    def _replace_receipt(
        self,
        *,
        claim_id: UUID,
        upload: ReceiptUpload,
    ) -> tuple[Claim, Receipt]:
        """Append a clearer receipt to an existing non-terminal claim."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        current_status = ClaimStatus(claim.status)
        if current_status not in (
            ClaimStatus.PROCESSING,
            ClaimStatus.NEEDS_CLARIFICATION,
            ClaimStatus.ESCALATED,
        ):
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "Claim cannot accept a replacement receipt in its current state.",
                409,
            )

        candidate = self._prepare_receipt(upload, set())
        if len(self._receipts.list_for_claim(claim_id)) >= self._settings.max_receipts_per_claim:
            raise ApplicationError("too_many_receipts", "Claim has reached its receipt limit.", 422)
        if self._receipts.find_claim_id_by_content_hash(candidate.content_hash):
            raise ApplicationError(
                ErrorCode.DUPLICATE_RECEIPT,
                "A receipt with the same content has already been submitted.",
                409,
            )

        now = datetime.now(UTC)
        previous_receipts = list(self._receipts.list_for_claim(claim_id))
        superseded_ids = {item.replaces_receipt_id for item in previous_receipts}
        active = [item for item in previous_receipts if item.id not in superseded_ids]
        replaced = active[-1] if active else None
        claim = claim.model_copy(update={
            "status": ClaimStatus.PROCESSING, "updated_at": now,
            "current_decision_id": None, "receipt_revision": claim.receipt_revision + 1,
        })
        reference = self._storage.put(
            candidate.content,
            filename=candidate.filename,
            media_type=candidate.media_type,
        )
        receipt = Receipt(
            id=uuid4(),
            claim_id=claim_id,
            original_filename=candidate.filename,
            media_type=candidate.media_type,
            storage_reference=reference,
            content_hash=candidate.content_hash,
            quality_score=Decimal(str(candidate.quality_score)),
            quality_findings=candidate.quality_findings,
            replaces_receipt_id=replaced.id if replaced else None,
            created_at=now,
        )
        self._receipts.save(receipt)
        self._claims.save(claim)
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim_id,
            event_type="receipt.replaced",
            actor_type=ActorType.EMPLOYEE,
            safe_payload={
                "receipt_id": str(receipt.id),
                "media_type": receipt.media_type,
            },
        )
        return claim, receipt

    def _prepare_receipt(
        self, upload: ReceiptUpload, seen_hashes: set[str]
    ) -> PreparedReceipt:
        filename = _safe_filename(upload.filename)
        if not filename:
            raise ApplicationError(
                ErrorCode.INVALID_FILE, "A filename is required.", 422
            )
        media_type = upload.media_type or ""
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise ApplicationError(
                ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                "Only JPG, PNG, and PDF files are supported.",
                415,
            )
        content = upload.content
        if len(content) > self._settings.max_receipt_size_bytes:
            raise ApplicationError(
                ErrorCode.FILE_TOO_LARGE,
                "Receipt exceeds the maximum allowed size.",
                413,
                {"max_bytes": self._settings.max_receipt_size_bytes},
            )
        if not content:
            raise ApplicationError(
                ErrorCode.INVALID_FILE, "Receipt file is empty.", 422
            )
        expected_signatures = ALLOWED_MEDIA_TYPES[media_type]
        if not any(content.startswith(signature) for signature in expected_signatures):
            raise ApplicationError(
                ErrorCode.INVALID_FILE,
                "Receipt content does not match its declared media type.",
                422,
            )
        content_hash = sha256(content).hexdigest()
        if content_hash in seen_hashes:
            raise ApplicationError(
                ErrorCode.DUPLICATE_RECEIPT,
                "The same receipt was uploaded more than once.",
                409,
            )
        score, findings = self._quality.check(content, media_type=media_type)
        return PreparedReceipt(
            filename=filename,
            media_type=media_type,
            content=content,
            content_hash=content_hash,
            quality_score=score,
            quality_findings=findings,
        )


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return ""
    name = PurePath(filename).name.strip()
    if not name or len(name) > MAX_FILENAME_LENGTH:
        return ""
    return name


def parse_declared_amount(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ApplicationError(
            ErrorCode.INVALID_CLAIM, "declared_amount must be a valid decimal.", 422
        ) from exc
    if not amount.is_finite() or amount <= 0 or amount > Decimal("999999999999.99"):
        raise ApplicationError(
            ErrorCode.INVALID_CLAIM,
            "declared_amount must be finite, positive, and at most 999999999999.99.",
            422,
        )
    return amount
