from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_receipt_extractor
from app.config import Settings
from app.integrations.llm import LlmReceiptExtractor
from app.integrations.masking import SensitiveDataMasker
from app.integrations.mock import MockReceiptExtractor
from app.main import app
from app.schemas.core import FieldConfidence

client = TestClient(app)


class DistinctReceiptExtractor(MockReceiptExtractor):
    def extract(self, **kwargs):
        result = super().extract(**kwargs)
        number = int(kwargs["receipt"].original_filename.split(".")[0])
        return result.model_copy(update={
            "vendor": FieldConfidence(value=f"Vendor {number}", confidence=1),
            "receipt_date": FieldConfidence(
                value=datetime.now(UTC).date() - timedelta(days=number), confidence=1,
            ),
        })


@pytest.mark.parametrize("count,amount,expected", [
    (1, "70000", "approved"),
    (8, "62500", "approved"),
    (8, "70000", "escalated"),
])
def test_review_threshold_uses_sum_of_active_receipts(count, amount, expected):
    app.dependency_overrides[get_receipt_extractor] = DistinctReceiptExtractor
    try:
        response = client.post("/claims", data={"employee_id": "audit", "declared_amount": amount},
            files=[("files", (f"{number}.pdf", f"%PDF-1.7\nCATEGORY:MEALS {number}\n%%EOF".encode(),
                               "application/pdf")) for number in range(count)])
        assert response.status_code == 201
        claim_id = response.json()["claim"]["id"]
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 200
        body = response.json()
        assert body["claim"]["status"] == expected
        if expected == "escalated":
            assert "auto_approve_amount_limit" in body["decision"]["reason_codes"]
        assert client.post(f"/claims/{claim_id}/process").json() == body
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


class StructuredModel:
    def __init__(self, output):
        self.output = output

    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, _messages):
        return self.output


def live_process(items, *, complete=True, subtotal=None, tax=None, discount=None):
    output = {
        "vendor": "Neutral Restaurant", "receipt_date": str(datetime.now(UTC).date()),
        "total": "60000", "currency": "IDR", "category": "meals", "confidence": 1,
        "line_items": items, "line_items_complete": complete,
        "subtotal": subtotal, "tax": tax, "discount": discount,
    }
    settings = Settings(_env_file=None, provider_mode="live", llm_model="synthetic",
                        llm_api_key="synthetic", llm_image_privacy_mode="send")
    extractor = LlmReceiptExtractor(settings, SensitiveDataMasker(), model=StructuredModel(output))
    app.dependency_overrides[get_receipt_extractor] = lambda: extractor
    image = BytesIO()
    Image.new("RGB", (8, 8), "white").save(image, format="PNG")
    try:
        response = client.post("/claims", data={"employee_id": "audit"},
                               files={"files": ("receipt.png", image.getvalue(), "image/png")})
        assert response.status_code == 201
        claim_id = response.json()["claim"]["id"]
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 200, response.text
        return response.json()
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


def item(description="Rice meal", total="60000"):
    return {"description": description, "quantity": 1, "unit_price": total, "total": total}


def test_live_item_evidence_reaches_prohibited_purchase_rule():
    body = live_process([item("Beer alcohol")])
    assert body["extractions"][0]["line_items"][0]["description"] == "Beer alcohol"
    assert body["claim"]["status"] == "rejected"
    assert "prohibited_item" in body["decision"]["reason_codes"]


@pytest.mark.parametrize("items,complete", [([], True), ([item()], False)])
def test_incomplete_live_item_evidence_cannot_auto_approve(items, complete):
    body = live_process(items, complete=complete)
    assert body["claim"]["status"] == "needs_clarification"
    assert "line_items_incomplete" in body["decision"]["reason_codes"]


@pytest.mark.parametrize("subtotal,tax,discount,item_total", [
    (None, None, None, "60000"),
    ("55000", "10000", "5000", "55000"),
    (None, "10000", "5000", "55000"),
])
def test_complete_live_items_preserve_approval_and_printed_adjustments(subtotal, tax, discount, item_total):
    body = live_process([item(total=item_total)], subtotal=subtotal, tax=tax, discount=discount)
    assert body["claim"]["status"] == "approved"
    assert not body["extractions"][0]["line_items_derived"]


def test_inconsistent_observed_item_totals_request_clarification():
    body = live_process([item(total="30000")])
    assert body["claim"]["status"] == "needs_clarification"
    assert "total_line_item_mismatch" in body["decision"]["reason_codes"]
