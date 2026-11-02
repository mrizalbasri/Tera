from decimal import Decimal
from io import BytesIO

from fastapi.testclient import TestClient

from app.api.deps import get_receipt_extractor
from app.main import app
from app.schemas.core import FieldConfidence

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
    assert payload["claim"]["status"] == "approved"
    assert payload["decision"]["outcome"] == "approved"
    assert payload["extractions"][0]["vendor"]["value"] == "Synthetic Vendor"
    assert payload["extractions"][0]["total"]["value"] == "60000"
    assert payload["attempts"][0]["attempt"] == 1
    assert payload["clarification"] is None


def test_processing_run_is_linked_to_attempts_and_extractions() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nrun-linkage\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    payload = response.json()
    run_id = payload["attempts"][0]["processing_run_id"]
    assert run_id is not None
    assert payload["extractions"][0]["processing_run_id"] == run_id

    detail = client.get(f"/claims/{claim_id}").json()
    assert detail["attempts"][0]["processing_run_id"] == run_id


def test_low_confidence_extraction_retries_and_requests_clarification() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nLOW_CONFIDENCE\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"]["status"] == "needs_clarification"
    assert len(payload["attempts"]) == 3
    assert payload["clarification"]["code"] == "extraction_confidence_low"
    assert "bukti lebih jelas" in payload["clarification"]["message"]
    assert "receipt_date" in payload["clarification"]["fields"]


def test_retry_with_preprocessing_can_recover_extraction() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nLOW_CONFIDENCE RETRY_THEN_SUCCESS\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"]["status"] == "approved"
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


def test_failed_run_can_be_retried_and_creates_new_run() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nMALFORMED-RETRY-FIXTURE\n%%EOF")

    first = client.post(f"/claims/{claim_id}/process")
    second = client.post(f"/claims/{claim_id}/process")

    assert first.status_code == 502
    assert second.status_code == 502
    detail = client.get(f"/claims/{claim_id}").json()
    assert detail["claim"]["status"] == "processing"
    run_ids = {attempt["processing_run_id"] for attempt in detail["attempts"]}
    assert len(run_ids) == 2


class InvalidOutputExtractor:
    """Extractor whose output violates the extraction schema (no bytes needed)."""

    provider_name = "invalid"

    def extract(self, **_kwargs):
        # Constructing an out-of-range confidence raises ValidationError.
        FieldConfidence(value="x", confidence=Decimal("2"))


def test_schema_invalid_provider_output_is_classified_error() -> None:
    claim_id = _create_claim(b"%PDF-1.7\ninvalid-output\n%%EOF")
    app.dependency_overrides[get_receipt_extractor] = lambda: InvalidOutputExtractor()
    try:
        response = client.post(f"/claims/{claim_id}/process")
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)

    assert response.status_code == 502
    assert response.json()["code"] == "malformed_extraction"


def test_low_confidence_on_any_receipt_requests_clarification() -> None:
    # The low-confidence receipt is uploaded FIRST; only a min-aggregate
    # confidence check catches it (the old last-result check did not).
    response = client.post(
        "/claims",
        data={"employee_id": "extraction-test", "declared_amount": "60000"},
        files=[
            (
                "files",
                (
                    "blurry.pdf",
                    BytesIO(b"%PDF-1.7\nLOW_CONFIDENCE-SECOND-RECEIPT\n%%EOF"),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "sharp.pdf",
                    BytesIO(b"%PDF-1.7\nsynthetic-sharp\n%%EOF"),
                    "application/pdf",
                ),
            ),
        ],
    )
    assert response.status_code == 201
    claim_id = response.json()["claim"]["id"]

    process = client.post(f"/claims/{claim_id}/process")

    assert process.status_code == 200
    assert process.json()["claim"]["status"] == "needs_clarification"
    assert process.json()["clarification"]["code"] == "extraction_confidence_low"


def test_claim_detail_includes_extraction_attempts() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nsynthetic-detail\n%%EOF")
    client.post(f"/claims/{claim_id}/process")

    response = client.get(f"/claims/{claim_id}")

    assert response.status_code == 200
    assert len(response.json()["extractions"]) == 1
    assert len(response.json()["attempts"]) == 1
