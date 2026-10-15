import asyncio
from dataclasses import dataclass, field
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.errors import ApplicationError
from app.services.intake import IntakeService
from app.services.uploads import ReceiptUploadService


@dataclass
class IncomingFile:
    content: bytes
    filename: str = "synthetic.pdf"
    content_type: str = "application/pdf"
    read_sizes: list[int] = field(default_factory=list)

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.content[:size]


def submit(service, files, **kwargs):
    return asyncio.run(service.create_claim(
        employee_id="synthetic", currency="IDR", declared_amount=None,
        files=files, idempotency_key=None, **kwargs,
    ))


def test_upload_count_is_rejected_before_reading_or_persisting():
    intake = Mock(spec=IntakeService)
    service = ReceiptUploadService(intake, Settings(_env_file=None, max_receipts_per_claim=1))
    files = [IncomingFile(b"%PDF-one"), IncomingFile(b"%PDF-two")]
    with pytest.raises(ApplicationError) as caught:
        submit(service, files)
    assert caught.value.code == "too_many_receipts"
    assert all(not upload.read_sizes for upload in files)
    intake.create_claim.assert_not_called()


def test_upload_reads_only_remaining_total_plus_one_byte():
    intake = Mock(spec=IntakeService)
    service = ReceiptUploadService(intake, Settings(
        _env_file=None, max_receipt_size_bytes=20, max_upload_total_bytes=10,
    ))
    files = [IncomingFile(b"%PDF-one"), IncomingFile(b"%PDF-two"), IncomingFile(b"%PDF-three")]
    with pytest.raises(ApplicationError) as caught:
        submit(service, files)
    assert caught.value.code == "upload_too_large"
    assert files[0].read_sizes == [11]
    assert files[1].read_sizes == [3]
    assert not files[2].read_sizes
    intake.create_claim.assert_not_called()


def test_replacement_rejects_oversize_without_persisting():
    from uuid import uuid4

    intake = Mock(spec=IntakeService)
    service = ReceiptUploadService(intake, Settings(_env_file=None, max_receipt_size_bytes=8))
    upload = IncomingFile(b"%PDF-too-large")
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(service.replace_receipt(claim_id=uuid4(), file=upload))
    assert caught.value.code == "file_too_large"
    assert upload.read_sizes == [9]
    intake.replace_receipt.assert_not_called()


@pytest.mark.parametrize("private", [True, False])
def test_duplicate_error_hides_other_claim_only_for_employee(private):
    intake = Mock(spec=IntakeService)
    intake.create_claim.side_effect = ApplicationError(
        "duplicate_receipt", "Receipt already submitted.", 409, {"claim_id": "other-claim"},
    )
    service = ReceiptUploadService(intake, Settings(_env_file=None))
    with pytest.raises(ApplicationError) as caught:
        submit(service, [IncomingFile(b"%PDF-duplicate")], hide_duplicate_details=private)
    assert caught.value.code == "duplicate_receipt"
    assert caught.value.status_code == 409
    assert bool(caught.value.details) is not private
