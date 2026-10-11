from io import BytesIO
from uuid import UUID

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


def test_oversized_receipt_is_rejected_with_typed_error(limited_size_client) -> None:
    response = limited_size_client.post(
        "/claims",
        data={"employee_id": "employee-oversize"},
        files={
            "files": (
                "receipt.png",
                BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 100),
                "image/png",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"
    assert response.json()["details"]["max_bytes"] == 64


def test_empty_receipt_is_rejected_with_typed_error() -> None:
    response = client.post(
        "/claims",
        data={"employee_id": "employee-empty"},
        files={"files": ("receipt.png", BytesIO(b""), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_duplicate_receipt_content_across_claims_is_rejected() -> None:
    content = b"\x89PNG\r\n\x1a\nduplicate-png-content"

    first = client.post(
        "/claims",
        data={"employee_id": "employee-dup-1"},
        files={"files": ("first.png", BytesIO(content), "image/png")},
    )
    second = client.post(
        "/claims",
        data={"employee_id": "employee-dup-2"},
        files={"files": ("second.png", BytesIO(content), "image/png")},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "duplicate_receipt"
    assert second.json()["details"]["claim_id"] == first.json()["claim"]["id"]


def test_receipt_with_invalid_filename_is_rejected() -> None:
    response = client.post(
        "/claims",
        data={"employee_id": "employee-filename"},
        files={"files": ("   ", BytesIO(b"\x89PNG\r\n\x1a\nvalid"), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_invalid_declared_amount_is_rejected_with_typed_error() -> None:
    response = client.post(
        "/claims",
        data={"employee_id": "employee-amount", "declared_amount": "not-a-number"},
        files={
            "files": (
                "receipt.pdf",
                BytesIO(b"%PDF-1.7\namount-fixture\n%%EOF"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_claim"


def test_claim_creation_appends_audit_event() -> None:
    from app.api.deps import _memory_repositories

    created = client.post(
        "/claims",
        data={"employee_id": "employee-audit"},
        files={
            "files": (
                "receipt.pdf",
                BytesIO(b"%PDF-1.7\naudit-fixture\n%%EOF"),
                "application/pdf",
            )
        },
    )
    claim_id = created.json()["claim"]["id"]

    events = _memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))

    assert [event.event_type for event in events] == ["claim.received"]
    assert events[0].actor_type == "employee"
    assert events[0].safe_payload["receipt_count"] == 1
