from datetime import UTC, datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from io import BytesIO
from uuid import uuid4

from app.api.deps import _memory_repositories
from app.domain.enums import ClaimStatus
from app.main import app
from app.schemas.core import Claim


client = TestClient(app)


def _create_claim(
    *,
    employee_id: str,
    content: bytes,
    filename: str = "receipt.pdf",
    declared_amount: str = "100000",
) -> dict:
    response = client.post(
        "/claims",
        data={"employee_id": employee_id, "declared_amount": declared_amount},
        files={"files": (filename, BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_replacement_receipt_succeeds_and_rejects_received_claim() -> None:
    created = _create_claim(
        employee_id="replacement-employee",
        content=b"%PDF-1.7\noriginal\n%%EOF",
    )
    claim_id = created["claim"]["id"]

    rejected = client.post(
        f"/claims/{claim_id}/receipts",
        files={"file": ("replacement.pdf", BytesIO(b"%PDF-1.7\nreplacement\n%%EOF"), "application/pdf")},
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "invalid_claim"

    processed = _create_claim(
        employee_id="replacement-employee-2",
        content=b"%PDF-1.7\nCATEGORY:HOTEL no-evidence\n%%EOF",
        declared_amount="400000",
    )
    processed_id = processed["claim"]["id"]
    process = client.post(f"/claims/{processed_id}/process")
    assert process.status_code == 200
    assert process.json()["claim"]["status"] == "needs_clarification"

    replacement = client.post(
        f"/claims/{processed_id}/receipts",
        files={"file": ("clearer.pdf", BytesIO(b"%PDF-1.7\nclearer receipt\n%%EOF"), "application/pdf")},
    )
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["claim"]["status"] == "processing"
    assert replacement.json()["receipt"]["original_filename"] == "clearer.pdf"


def test_report_summary_and_csv_reflect_claims_and_zero_amount() -> None:
    now = datetime.now(UTC)
    claim = Claim(
        id=uuid4(),
        employee_id="report-employee",
        status=ClaimStatus.RECEIVED,
        submitted_at=now,
        currency="IDR",
        declared_amount=Decimal("0"),
        created_at=now,
        updated_at=now,
    )
    _memory_repositories().claims.save(claim)
    claim_id = str(claim.id)

    summary = client.get("/reports/summary", params={"employee_id": "report-employee"})
    assert summary.status_code == 200
    assert summary.json()["total_claims"] == 1
    assert summary.json()["pending_claims"] == 1

    export = client.get("/reports/claims.csv", params={"employee_id": "report-employee"})
    assert export.status_code == 200
    lines = export.text.splitlines()
    assert lines[0] == "claim_id,employee_id,submitted_at,currency,declared_amount,status"
    assert claim_id in lines[1]
    assert ",0.00,received" in lines[1] or ",0,received" in lines[1]
