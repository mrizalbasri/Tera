from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_claim_accepts_pdf_and_returns_receipt_metadata() -> None:
    response = client.post(
        "/claims",
        data={"employee_id": "employee-1", "currency": "idr", "declared_amount": "60000"},
        files={
            "files": (
                "receipt.pdf",
                BytesIO(b"%PDF-1.7\nsynthetic receipt\n%%EOF"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["claim"]["status"] == "received"
    assert payload["claim"]["currency"] == "IDR"
    assert len(payload["receipts"]) == 1
    assert payload["receipts"][0]["content_hash"]
    assert payload["receipts"][0]["storage_reference"].startswith("memory://")


def test_idempotency_key_replays_original_claim() -> None:
    files = {
        "files": (
            "receipt.png",
            BytesIO(b"\x89PNG\r\n\x1a\nsynthetic image"),
            "image/png",
        )
    }
    headers = {"Idempotency-Key": "submission-unique-1"}

    first = client.post(
        "/claims",
        data={"employee_id": "employee-2"},
        files=files,
        headers=headers,
    )
    second = client.post(
        "/claims",
        data={"employee_id": "employee-2"},
        files={
            "files": (
                "different.png",
                BytesIO(b"\x89PNG\r\n\x1a\ndifferent image"),
                "image/png",
            )
        },
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["idempotent_replay"] is True
    assert second.json()["claim"]["id"] == first.json()["claim"]["id"]


def test_unsupported_receipt_is_rejected_with_typed_error() -> None:
    response = client.post(
        "/claims",
        data={"employee_id": "employee-3"},
        files={"files": ("receipt.txt", BytesIO(b"not a receipt"), "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"


def test_claim_detail_and_employee_filter_return_receipts() -> None:
    created = client.post(
        "/claims",
        data={"employee_id": "employee-filter"},
        files={
            "files": (
                "receipt.jpg",
                BytesIO(b"\xff\xd8\xffsynthetic jpeg"),
                "image/jpeg",
            )
        },
    )
    claim_id = created.json()["claim"]["id"]

    detail = client.get(f"/claims/{claim_id}")
    listing = client.get("/claims", params={"employee_id": "employee-filter"})

    assert detail.status_code == 200
    assert detail.json()["claim"]["id"] == claim_id
    assert len(detail.json()["receipts"]) == 1
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
