from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_receipt_extractor
from app.config import Settings
from app.integrations.local_ocr import OcrFirstReceiptExtractor, OcrLine, RapidOcrReader, group_ocr_rows
from app.integrations.ocr_parser import parse_receipt
from app.main import app
from app.schemas.core import Receipt


def lines(*texts, confidence=0.99):
    return tuple(OcrLine(text, Decimal(str(confidence))) for text in texts)


CLEAR = lines(
    "WARUNG SINTETIS",
    "Tanggal: 2026-11-10",
    "Nasi ayam 2 x 25.000 50.000",
    "Teh manis 1 x 10.000 10.000",
    "TOTAL Rp 60.000",
    "Terima kasih",
)


def receipt():
    return Receipt(
        id=uuid4(), claim_id=uuid4(), original_filename="synthetic.png",
        media_type="image/png", storage_reference="memory:synthetic",
        content_hash="a" * 64, created_at=datetime.now(UTC),
    )


def image_bytes():
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_clear_receipt_bypasses_external_model_and_preserves_item_evidence():
    ocr, fallback = Mock(), Mock()
    ocr.read.return_value = CLEAR
    extractor = OcrFirstReceiptExtractor(settings(), ocr, lambda: fallback)
    result = extractor.extract(receipt=receipt(), content=image_bytes(),
                               declared_amount=Decimal("999999"), attempt=1)
    assert result.total.value == Decimal("60000")
    assert result.vendor.value == "WARUNG SINTETIS"
    assert result.receipt_date.value.isoformat() == "2026-11-10"
    assert result.category.value == "meals"
    assert len(result.line_items) == 2
    assert result.line_items[0].quantity == 2
    assert result.line_items_complete is True
    assert result.line_items_derived is False
    assert result.provider.startswith("rapidocr:")
    fallback.extract.assert_not_called()
    fallback.extract_text.assert_not_called()


@pytest.mark.parametrize("texts", [
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "SUBTOTAL Rp 60.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "TOTAL Rp 60.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 60.000", "TOTAL Rp 60.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 50.000", "TOTAL Rp 60.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-02-30", "Nasi ayam 2 x 25.000 50.000", "TOTAL Rp 50.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 50.000", "TOTAL USD 50.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 50.000", "TOTAL Rp 50.000", "TOTAL Rp 60.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 50.000", "Rokok 10.000", "TOTAL Rp 50.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Nasi ayam 2 x 25.000 50.000", "Pajak 10%", "TOTAL Rp 50.000"],
    ["WARUNG SINTETIS", "Tanggal: 2026-11-10", "Tanggal: 2026-11-11", "Nasi ayam 2 x 25.000 50.000", "TOTAL Rp 50.000"],
])
def test_ambiguous_or_incomplete_evidence_never_uses_local_fast_path(texts):
    assert parse_receipt(lines(*texts)) is None


def test_breakdown_must_reconcile_independently():
    data = lines(
        "WARUNG SINTETIS", "Tanggal: 2026-11-10",
        "Nasi ayam 2 x 25.000 50.000", "Subtotal Rp 50.000",
        "Pajak Rp 5.000", "Diskon Rp 2.000", "TOTAL Rp 53.000",
    )
    output = parse_receipt(data)
    assert output.total == Decimal("53000")
    assert output.subtotal == Decimal("50000")
    assert output.tax == Decimal("5000")
    assert output.discount == Decimal("2000")


def test_unfamiliar_but_readable_layout_uses_text_not_vision():
    ocr, fallback = Mock(), Mock()
    ocr.read.return_value = lines("Unfamiliar layout", "Total Rp 60.000")
    result = OcrFirstReceiptExtractor(settings(), ocr, lambda: fallback).extract(
        receipt=receipt(), content=image_bytes(), declared_amount=None, attempt=1,
    )
    assert result is fallback.extract_text.return_value
    assert "Total Rp 60.000" in fallback.extract_text.call_args.kwargs["text"]
    fallback.extract.assert_not_called()


@pytest.mark.parametrize("data", [(), lines("Uncertain", confidence=0.4)])
def test_empty_or_weak_ocr_uses_existing_vision_boundary(data):
    ocr, fallback = Mock(), Mock()
    ocr.read.return_value = data
    OcrFirstReceiptExtractor(settings(), ocr, lambda: fallback).extract(
        receipt=receipt(), content=image_bytes(), declared_amount=None, attempt=1,
    )
    fallback.extract.assert_called_once()
    fallback.extract_text.assert_not_called()


def test_image_privacy_block_allows_local_but_never_external_fallback():
    ocr, fallback_factory = Mock(), Mock()
    ocr.read.return_value = CLEAR
    extractor = OcrFirstReceiptExtractor(
        settings(llm_image_privacy_mode="block"), ocr, fallback_factory,
    )
    assert extractor.extract(receipt=receipt(), content=image_bytes(),
                             declared_amount=None, attempt=1).total.value == 60000
    ocr.read.return_value = lines("Unfamiliar layout")
    from app.errors import ApplicationError
    with pytest.raises(ApplicationError) as exc:
        extractor.extract(receipt=receipt(), content=image_bytes(), declared_amount=None, attempt=1)
    assert exc.value.code == "image_privacy_blocked"
    fallback_factory.assert_not_called()


def test_local_extraction_runs_through_real_claim_pipeline():
    ocr = Mock()
    ocr.read.return_value = CLEAR
    fallback_factory = Mock(side_effect=AssertionError("must not invoke AI"))
    app.dependency_overrides[get_receipt_extractor] = lambda: OcrFirstReceiptExtractor(
        settings(), ocr, fallback_factory,
    )
    try:
        client = TestClient(app)
        created = client.post("/claims", files={"files": (
            "synthetic.png", image_bytes(), "image/png",
        )})
        assert created.status_code == 201
        claim_id = created.json()["claim"]["id"]
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 200
        result = response.json()
        assert result["extractions"][0]["provider"].startswith("rapidocr:")
        assert result["extractions"][0]["line_items_complete"] is True
        assert result["claim"]["amount"]["value"] == "60000"
        fallback_factory.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


def test_grouping_preserves_columns_and_weak_text():
    output = SimpleNamespace(
        txts=["60.000", "TOTAL Rp", "Nasi ayam", "2 x 25.000", "50.000", "Rokok"],
        scores=[0.99, 0.98, 0.99, 0.99, 0.99, 0.3],
        boxes=[
            [[300, 80], [400, 80], [400, 100], [300, 100]],
            [[0, 80], [100, 80], [100, 100], [0, 100]],
            [[0, 40], [100, 40], [100, 60], [0, 60]],
            [[150, 41], [240, 41], [240, 61], [150, 61]],
            [[300, 40], [400, 40], [400, 60], [300, 60]],
            [[0, 120], [100, 120], [100, 140], [0, 140]],
        ],
    )
    result = group_ocr_rows(output)
    assert [line.text for line in result] == ["Nasi ayam 2 x 25.000 50.000", "TOTAL Rp 60.000", "Rokok"]
    assert result[-1].confidence == Decimal("0.3")


def test_cache_is_bounded_expires_and_does_not_retain_images(monkeypatch):
    import app.integrations.local_ocr as module

    reader = RapidOcrReader()
    engine = Mock(return_value=SimpleNamespace(txts=None, boxes=None, scores=None))
    reader._engine = engine
    clock = [0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    content = image_bytes()
    assert reader.read(content, "image/png") == ()
    assert reader.read(content, "image/png") == ()
    assert engine.call_count == 1
    clock[0] = 121
    reader.read(content, "image/png")
    assert engine.call_count == 2
    for index in range(40):
        buffer = BytesIO()
        Image.new("RGB", (32, 32), (index, 0, 0)).save(buffer, format="PNG")
        reader.read(buffer.getvalue(), "image/png")
    assert len(reader._cache) == 32
    assert all(isinstance(value[1], tuple) for value in reader._cache.values())


def test_reader_rejects_invalid_images_before_model_inference():
    from app.errors import ApplicationError

    reader = RapidOcrReader()
    reader._engine = Mock()
    with pytest.raises(ApplicationError) as error:
        reader.read(b"not a PNG", "image/png")
    assert error.value.code == "image_sanitization_failed"
    reader._engine.assert_not_called()


def test_orientation_is_applied_before_ocr_and_metadata_removed():
    reader = RapidOcrReader()
    reader._engine = Mock(return_value=SimpleNamespace(txts=None, boxes=None, scores=None))
    image = Image.new("RGB", (80, 40), "white")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "synthetic private metadata"
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    reader.read(buffer.getvalue(), "image/jpeg")
    pixels = reader._engine.call_args.args[0]
    with Image.open(BytesIO(pixels)) as forwarded:
        assert forwarded.size == (40, 80)
        assert not forwarded.getexif()
    assert b"synthetic private metadata" not in pixels


def test_dependency_reuses_warmed_reader_and_keeps_mock_mode_unchanged(monkeypatch):
    from app.api import deps
    import app.integrations.local_ocr as module
    from app.integrations.mock import MockReceiptExtractor
    from app.integrations.masking import SensitiveDataMasker

    factory = Mock()
    monkeypatch.setattr(module, "RapidOcrReader", factory)
    deps._local_ocr_reader.cache_clear()
    configured = settings(provider_mode="live", llm_api_key="synthetic", receipt_extraction_mode="ocr_first")
    try:
        deps.warm_receipt_ocr(configured)
        first = deps.get_receipt_extractor(configured, SensitiveDataMasker())
        second = deps.get_receipt_extractor(configured, SensitiveDataMasker())
        assert first._reader is second._reader
        factory.assert_called_once_with(2)
        factory.return_value.ready.assert_called_once()
        assert isinstance(deps.get_receipt_extractor(
            settings(provider_mode="mock", receipt_extraction_mode="ocr_first"), SensitiveDataMasker(),
        ), MockReceiptExtractor)
    finally:
        deps._local_ocr_reader.cache_clear()


def test_missing_ocr_dependency_fails_readiness_without_exposing_details(monkeypatch):
    from app.api import deps
    from app.config import get_settings

    monkeypatch.setattr(deps, "_local_ocr_reader", Mock(side_effect=RuntimeError("private model path")))
    app.dependency_overrides[get_settings] = lambda: settings(
        provider_mode="live", llm_api_key="synthetic", receipt_extraction_mode="ocr_first",
    )
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "private" not in response.text


def test_text_fallback_masks_sensitive_data_and_does_not_send_images():
    from app.integrations.llm_prompt import build_text_extraction_message
    from app.integrations.masking import SensitiveDataMasker

    message = build_text_extraction_message(
        SensitiveDataMasker(), "synthetic@example.test 081234567890 TOTAL Rp 60.000", None,
    )
    assert all(part["type"] == "text" for part in message.content)
    text = str(message.content)
    assert "synthetic@example.test" not in text
    assert "081234567890" not in text
    assert "60.000" in text
    assert "untrusted OCR evidence" in text


def test_text_fallback_uses_real_structured_transport_and_usage_capture():
    import json
    import httpx
    from langchain_openai import ChatOpenAI
    from app.integrations.llm import LlmReceiptExtractor
    from app.integrations.masking import SensitiveDataMasker

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "synthetic", "object": "chat.completion", "created": 0,
            "model": "synthetic", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": parse_receipt(CLEAR).model_dump_json()}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125},
        })

    configured = settings(llm_api_key="synthetic", llm_model="synthetic")
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        model = ChatOpenAI(model="synthetic", api_key="synthetic",
                           base_url="http://localhost:1234/v1", http_client=transport, max_retries=0)
        extractor = LlmReceiptExtractor(configured, SensitiveDataMasker(), model=model)
        result = extractor.extract_text(
            receipt=receipt(), text="synthetic@example.test TOTAL Rp 60.000",
            declared_amount=None, attempt=1,
        )
    assert len(requests) == 1
    payload = requests[0]
    assert payload["response_format"] == {"type": "json_object"}
    assert all(part["type"] == "text" for part in payload["messages"][0]["content"])
    assert "synthetic@example.test" not in str(payload)
    assert result.total.value == 60000
    assert result.line_items_complete is True
    assert result.provider == "ocr-text:synthetic:attempt-1"
    assert result.provider_usage["status"] == "measured"


def test_missing_bundled_models_never_triggers_a_download(monkeypatch, tmp_path):
    import sys
    from types import ModuleType

    package = ModuleType("rapidocr")
    package.__file__ = str(tmp_path / "__init__.py")
    package.RapidOCR = Mock()
    monkeypatch.setitem(sys.modules, "rapidocr", package)
    with pytest.raises(RuntimeError, match="models are missing"):
        RapidOcrReader().ready()
    package.RapidOCR.assert_not_called()
