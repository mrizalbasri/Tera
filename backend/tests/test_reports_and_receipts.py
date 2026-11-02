from datetime import UTC, datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from io import BytesIO
from uuid import UUID, uuid4

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


def test_get_receipt_content_returns_file() -> None:
    created = _create_claim(
        employee_id="content-employee",
        content=b"%PDF-1.7\ntest receipt content\n%%EOF",
        filename="my-nota.pdf",
    )
    claim_id = created["claim"]["id"]
    receipt_id = created["receipts"][0]["id"]

    response = client.get(f"/claims/{claim_id}/receipts/{receipt_id}/content")
    assert response.status_code == 200
    assert response.content == b"%PDF-1.7\ntest receipt content\n%%EOF"
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="my-nota.pdf"' in response.headers.get("content-disposition", "")


def test_receipt_content_supports_unicode_filename() -> None:
    created = _create_claim(
        employee_id="unicode-content-employee",
        content=b"%PDF-1.7\nunicode receipt\n%%EOF",
        filename="nota-東京.pdf",
    )
    claim_id = created["claim"]["id"]
    receipt_id = created["receipts"][0]["id"]
    response = client.get(f"/claims/{claim_id}/receipts/{receipt_id}/content")
    assert response.status_code == 200
    assert "filename*=UTF-8''nota-%E6%9D%B1%E4%BA%AC.pdf" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_receipt_content_rejects_receipt_from_another_claim() -> None:
    first = _create_claim(employee_id="first-content", content=b"%PDF-1.7\nfirst\n%%EOF")
    second = _create_claim(employee_id="second-content", content=b"%PDF-1.7\nsecond\n%%EOF")
    response = client.get(f"/claims/{first['claim']['id']}/receipts/{second['receipts'][0]['id']}/content")
    assert response.status_code == 404


def test_clearer_receipt_starts_a_new_run_and_preserves_original_evidence() -> None:
    created = _create_claim(
        employee_id="retake-employee",
        content=b"%PDF-1.7\nLOW_CONFIDENCE CATEGORY:MEALS\n%%EOF",
        declared_amount="60000",
    )
    claim_id = created["claim"]["id"]
    first = client.post(f"/claims/{claim_id}/process").json()
    assert first["claim"]["status"] == "needs_clarification"
    replacement = client.post(f"/claims/{claim_id}/receipts", files={
        "file": ("clearer.pdf", b"%PDF-1.7\nCATEGORY:MEALS clearer\n%%EOF", "application/pdf")
    })
    assert replacement.status_code == 201
    result = client.post(f"/claims/{claim_id}/process")
    assert result.status_code == 200, result.text
    assert result.json()["claim"]["status"] == "approved"
    assert {item["receipt_id"] for item in result.json()["extractions"]} == {replacement.json()["receipt"]["id"]}
    detail = client.get(f"/claims/{claim_id}").json()
    assert len(detail["receipts"]) == 2
    clarifications = client.get(f"/claims/{claim_id}/clarifications").json()["items"]
    assert all(item["status"] != "open" for item in clarifications)
    repeated = client.post(f"/claims/{claim_id}/process").json()
    assert repeated["decision"]["id"] == result.json()["decision"]["id"]


def test_replacement_preserves_other_receipts_in_a_multi_receipt_claim(monkeypatch) -> None:
    identifiers = iter([UUID(int=1000), UUID(int=2), UUID(int=1), UUID(int=3)])
    monkeypatch.setattr("app.services.intake.uuid4", lambda: next(identifiers))
    response = client.post("/claims", data={"employee_id": "multi-retake", "declared_amount": "60000"}, files=[
        ("files", ("first.pdf", b"%PDF-1.7\nCATEGORY:MEALS first\n%%EOF", "application/pdf")),
        ("files", ("blurred.pdf", b"%PDF-1.7\nLOW_CONFIDENCE CATEGORY:MEALS second\n%%EOF", "application/pdf")),
    ])
    assert response.status_code == 201
    created = response.json()
    claim_id = created["claim"]["id"]
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "needs_clarification"
    replacement = client.post(f"/claims/{claim_id}/receipts", files={
        "file": ("clear-second.pdf", b"%PDF-1.7\nCATEGORY:MEALS clear second\n%%EOF", "application/pdf")
    })
    assert replacement.status_code == 201
    assert replacement.json()["receipt"]["replaces_receipt_id"] == created["receipts"][-1]["id"]
    result = client.post(f"/claims/{claim_id}/process")
    assert result.status_code == 200, result.text
    assert result.json()["claim"]["status"] == "approved"
    assert {item["receipt_id"] for item in result.json()["extractions"]} == {
        created["receipts"][0]["id"], replacement.json()["receipt"]["id"],
    }


def test_replacement_reopens_review_without_duplicate_open_queue_entries() -> None:
    created = _create_claim(employee_id="review-retake", content=b"%PDF-1.7\nreview original\n%%EOF", declared_amount="700000")
    claim_id = created["claim"]["id"]
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "escalated"
    replacement = client.post(f"/claims/{claim_id}/receipts", files={
        "file": ("clear-review.pdf", b"%PDF-1.7\nreview replacement\n%%EOF", "application/pdf")
    })
    assert replacement.status_code == 201
    result = client.post(f"/claims/{claim_id}/process")
    assert result.status_code == 200, result.text
    assert result.json()["claim"]["status"] == "escalated"
    queue = client.get("/reviews").json()
    assert queue["total"] == 1
    assert queue["items"][0]["claim"]["id"] == claim_id
