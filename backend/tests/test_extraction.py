from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_claim(content: bytes, filename: str = "receipt.pdf") -> str:
    response = client.post(
        "/claims",
        data={"employee_id": "extraction-test", "declared_amount": "60000"},
        files={"files": (filename, BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["claim"]["id"]


def test_process_claim_returns_typed_extraction() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nsynthetic\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"]["status"] == "received"
    assert payload["extractions"][0]["vendor"]["value"] == "Synthetic Vendor"
    assert payload["extractions"][0]["total"]["value"] == "60000"
    assert payload["attempts"][0]["attempt"] == 1
    assert payload["clarification"] is None


def test_low_confidence_extraction_retries_and_requests_clarification() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nLOW_CONFIDENCE\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"]["status"] == "needs_clarification"
    assert len(payload["attempts"]) == 3
    assert payload["clarification"]["code"] == "extraction_confidence_low"
    assert "clearer receipt" in payload["clarification"]["message"]


def test_retry_with_preprocessing_can_recover_extraction() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nLOW_CONFIDENCE RETRY_THEN_SUCCESS\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"]["status"] == "received"
    assert len(payload["attempts"]) == 2
    assert payload["attempts"][0]["preprocessing"] == []
    assert payload["attempts"][1]["preprocessing"] == ["normalize_document"]
    assert payload["attempts"][1]["confidence"]["total"] == "0.96"
    assert payload["clarification"] is None


def test_exhausted_processing_is_idempotent() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nLOW_CONFIDENCE IDEMPOTENT\n%%EOF")

    first = client.post(f"/claims/{claim_id}/process")
    second = client.post(f"/claims/{claim_id}/process")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_malformed_extraction_is_explicit_error() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nMALFORMED\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 502
    assert response.json()["code"] == "malformed_extraction"


def test_claim_detail_includes_extraction_attempts() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nsynthetic-detail\n%%EOF")
    client.post(f"/claims/{claim_id}/process")

    response = client.get(f"/claims/{claim_id}")

    assert response.status_code == 200
    assert len(response.json()["extractions"]) == 1
    assert len(response.json()["attempts"]) == 1
