"""M7 tests: masking boundary (FR-13), LangChain adapter, error taxonomy."""

from decimal import Decimal
import json
from io import BytesIO

import httpx
import openai
import pytest
import zlib
from fastapi.testclient import TestClient
from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI
from PIL import Image
from pydantic import BaseModel, Field

from app.config import Settings
from app.api.deps import get_receipt_extractor, get_sensitive_data_masker
from app.domain.enums import ErrorClassification
from app.errors import ApplicationError
from app.integrations.llm import LlmExtractionOutput, LlmReceiptExtractor
from app.integrations.masking import SensitiveDataMasker
from app.integrations.mock import MockReceiptExtractor
from app.main import app
from app.schemas.core import Receipt

client = TestClient(app)


def test_json_mode_request_includes_output_contract() -> None:
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(200, json={
            "id": "local-test", "object": "chat.completion", "created": 0,
            "model": "local-vision", "choices": [{"index": 0,
                "finish_reason": "stop", "message": {
                    "role": "assistant", "content": _valid_output().model_dump_json()
                }}],
        })

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = ChatOpenAI(model="local-vision", api_key="synthetic-key",
                           base_url="http://localhost:1234/v1", http_client=client,
                           max_retries=0)
        extractor = LlmReceiptExtractor(_settings(), SensitiveDataMasker(), model=model)
        result = extractor.extract(receipt=_receipt(), content=_jpeg_bytes(),
                                   declared_amount=None, attempt=1)
    assert result.total.value == Decimal("60000")
    assert len(requests) == 1
    payload = requests[0]
    assert payload["response_format"] == {"type": "json_object"}
    prompt = payload["messages"][0]["content"][0]["text"]
    assert "JSON" in prompt
    for field in LlmExtractionOutput.model_fields:
        assert field in prompt
    assert "YYYY-MM-DD" in prompt


@pytest.mark.parametrize("marker", [b"\xff\xfe", b"\xff\xe1", b"\xff\xed"])
def test_progressive_jpeg_metadata_between_scans_never_leaves(marker) -> None:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), (210, 205, 200)).save(
        buffer, format="JPEG", progressive=True
    )
    base = buffer.getvalue()
    scan_offsets = [i for i in range(len(base) - 1) if base[i:i + 2] == b"\xff\xda"]
    assert len(scan_offsets) > 1
    secret = b"GPS:-6.2,106.8 synthetic@example.test"
    content = base
    for offset in reversed(scan_offsets[1:]):
        content = content[:offset] + _jpeg_segment(marker, secret) + content[offset:]
    with Image.open(BytesIO(content)) as original:
        original.load()
        pixels = original.tobytes()
    extractor, stub = _extractor(structured=lambda _m: _valid_output())
    extractor.extract(receipt=_receipt(), content=content, declared_amount=None, attempt=1)
    sanitized = _outgoing_image_bytes(stub)
    assert secret not in sanitized
    assert sanitized == base
    with Image.open(BytesIO(sanitized)) as image:
        image.load()
        assert image.tobytes() == pixels


@pytest.mark.parametrize("exception_type,status,code", [
    (openai.BadRequestError, 400, "provider_invalid_request"),
    (openai.RateLimitError, 429, "provider_rate_limited"),
])
def test_provider_logs_never_include_response_or_credentials(caplog, exception_type, status, code):
    secret = "synthetic@example.test sk-synthetic-secret"

    def failing(_messages):
        request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")
        raise exception_type(secret, response=httpx.Response(status, request=request),
                             body={"error": {"message": secret}})

    extractor, _ = _extractor(_settings(llm_max_retries=0, provider_fallback="none"),
                              structured=failing)
    with caplog.at_level("WARNING", logger="app.integrations.llm"):
        with pytest.raises(ApplicationError):
            extractor.extract(receipt=_receipt(), content=_jpeg_bytes(),
                              declared_amount=None, attempt=1)
    assert secret not in caplog.text
    assert code in caplog.text
    assert exception_type.__name__ in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def _settings(**overrides) -> Settings:
    defaults = {
        "_env_file": None,
        "provider_mode": "live",
        "llm_api_key": "test-key",
        "llm_max_retries": 1,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _receipt(media_type: str = "image/jpeg") -> Receipt:
    from datetime import UTC, datetime
    from uuid import uuid4

    return Receipt(
        id=uuid4(),
        claim_id=uuid4(),
        original_filename="receipt.jpg",
        media_type=media_type,
        storage_reference="memory://test",
        content_hash="a" * 64,
        quality_score=Decimal("1"),
        quality_findings=[],
        created_at=datetime.now(UTC),
    )


class StubStructured:
    """Replaces the LangChain structured model; captures outgoing prompts."""

    def __init__(self, fn) -> None:
        self._fn = fn
        self.calls: list[list] = []

    def invoke(self, messages):
        self.calls.append(messages)
        return self._fn(messages)


def _extractor(settings: Settings | None = None, structured=None) -> tuple[
    LlmReceiptExtractor, StubStructured | None
]:
    extractor = LlmReceiptExtractor(settings or _settings(), SensitiveDataMasker())
    stub = None
    if structured is not None:
        stub = StubStructured(structured)
        extractor._structured = stub
    return extractor, stub


def _valid_output() -> LlmExtractionOutput:
    return LlmExtractionOutput(
        vendor="Warung Bu Sari",
        receipt_date="2026-10-04",
        total=Decimal("60000"),
        currency="IDR",
        category="meals",
        confidence=Decimal("0.9"),
    )


@pytest.mark.parametrize("value", [None, ""])
def test_unreadable_date_preserves_total_without_inventing_date(value):
    output = _valid_output().model_dump()
    output["receipt_date"] = value
    extractor, _ = _extractor(structured=lambda _m: output)
    result = extractor.extract(receipt=_receipt(), content=_jpeg_bytes(),
                               declared_amount=None, attempt=1)
    assert result.receipt_date.value is None
    assert result.receipt_date.confidence == 0
    assert result.total.value == Decimal("60000")
    assert "receipt_date_unreadable" in result.warnings


def test_admitted_placeholder_date_is_not_treated_as_observed():
    output = _valid_output().model_dump()
    output.update(receipt_date="1970-01-01",
                  warnings=["Receipt date blurred; default date used"])
    extractor, _ = _extractor(structured=lambda _m: output)
    result = extractor.extract(receipt=_receipt(), content=_jpeg_bytes(),
                               declared_amount=None, attempt=1)
    assert result.receipt_date.value is None
    assert result.receipt_date.confidence == 0


def test_missing_date_requests_clarification_once_and_preserves_evidence():
    output = _valid_output().model_dump()
    output["receipt_date"] = None
    extractor, stub = _extractor(structured=lambda _m: output)
    app.dependency_overrides[get_receipt_extractor] = lambda: extractor
    try:
        created = client.post("/claims", data={"employee_id": "date-test"},
                              files={"files": ("receipt.jpg", _jpeg_bytes(), "image/jpeg")})
        claim_id = created.json()["claim"]["id"]
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 200
        body = response.json()
        assert body["claim"]["status"] == "needs_clarification"
        assert body["clarification"]["fields"] == ["receipt_date"]
        assert len(stub.calls) == 1
        assert body["extractions"][0]["total"]["value"] == "60000"
        assert body["extractions"][0]["receipt_date"]["value"] is None
        detail = client.get(f"/claims/{claim_id}").json()
        assert detail["extractions"][0]["receipt_date"]["value"] is None
        assert body["decision"] is None
        replay = client.post(f"/claims/{claim_id}/process")
        assert replay.status_code == 200
        assert replay.json() == body
        assert len(stub.calls) == 1
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


@pytest.mark.parametrize("total,quantity", [
    ("1e30", "1"), ("1e999999", "1e-999999"), ("0.01", "1e30"),
    ("1e30", "1e30"), ("1e-30", "1"), ("60000", "1e-30"),
])
def test_extreme_numbers_fail_safely_and_processing_can_retry(total, quantity, caplog):
    from uuid import UUID
    from app.api.deps import get_processing_run_repository

    output = _valid_output().model_copy(update={
        "total": Decimal(total), "quantity": Decimal(quantity),
    })
    extractor, stub = _extractor(
        _settings(provider_fallback="mock"), structured=lambda _messages: output,
    )
    app.dependency_overrides[get_receipt_extractor] = lambda: extractor
    try:
        created = client.post("/claims", data={"employee_id": "numeric-test"},
                              files={"files": ("receipt.jpg", _jpeg_bytes(), "image/jpeg")})
        assert created.status_code == 201
        claim_id = created.json()["claim"]["id"]
        headers = {"Idempotency-Key": "extreme-number-run"}
        response = client.post(f"/claims/{claim_id}/process", headers=headers)
        assert response.status_code == 502
        assert response.json()["code"] == "malformed_extraction"
        runs = get_processing_run_repository(Settings(_env_file=None, storage_backend="memory"))
        assert runs.latest_for_claim(UUID(claim_id)).status == "failed"
        calls = len(stub.calls)
        replay = client.post(f"/claims/{claim_id}/process", headers=headers)
        assert replay.status_code == 502
        assert len(stub.calls) == calls
        output = _valid_output()
        retry = client.post(f"/claims/{claim_id}/process")
        assert retry.status_code == 200
        assert runs.latest_for_claim(UUID(claim_id)).status != "running"
        assert total not in response.text
        assert total not in caplog.text
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


@pytest.mark.parametrize("total,quantity,unit_price", [
    ("0.01", "1000", "0.000010"), ("1", "3", "0.33"),
    ("999999999999.999999", "0.000001", "999999999999999999.00"),
])
def test_supported_numeric_precision_remains_valid(total, quantity, unit_price):
    output = _valid_output().model_copy(update={
        "total": Decimal(total), "quantity": Decimal(quantity),
    })
    extractor, _ = _extractor(structured=lambda _messages: output)
    result = extractor.extract(receipt=_receipt(), content=_jpeg_bytes(), declared_amount=None, attempt=1)
    assert result.line_items[0].unit_price == Decimal(unit_price)


def _jpeg_segment(marker: bytes, payload: bytes) -> bytes:
    return marker + (len(payload) + 2).to_bytes(2, "big") + payload


def _jpeg_bytes() -> bytes:
    """A real 4x4 JPEG with injected EXIF and comment segments.

    The COM segment doubles as the mock-extractor category marker: the mock
    reads the ORIGINAL content, while the provider receives the sanitized
    image with the comment stripped.
    """
    buffer = BytesIO()
    Image.new("RGB", (4, 4), (210, 205, 200)).save(buffer, format="JPEG")
    base = buffer.getvalue()
    exif_payload = b"Exif\x00\x00" + b"II*\x00" + b"GPS:-6.2,106.8 Device:PhoneX"
    return (
        base[:2]  # SOI
        + _jpeg_segment(b"\xff\xe1", exif_payload)
        + _jpeg_segment(b"\xff\xfe", b"handwritten-note CATEGORY:MEALS")
        + base[2:]
    )


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        len(payload).to_bytes(4, "big")
        + chunk_type
        + payload
        + zlib.crc32(chunk_type + payload).to_bytes(4, "big")
    )


def _png_bytes() -> bytes:
    """A real 4x4 PNG with an injected tEXt metadata chunk after IHDR."""
    buffer = BytesIO()
    Image.new("RGB", (4, 4), (210, 205, 200)).save(buffer, format="PNG")
    base = buffer.getvalue()
    ihdr_end = 8 + 25  # signature + full IHDR chunk (12 + 13)
    return base[:ihdr_end] + _png_chunk(b"tEXt", b"Comment\x00SECRET-GPS-DATA") + base[ihdr_end:]


def _png_chunk_with_crc(chunk_type: bytes, payload: bytes, crc: int) -> bytes:
    return (
        len(payload).to_bytes(4, "big") + chunk_type + payload + crc.to_bytes(4, "big")
    )


# --- Masker unit behaviour (FR-13) --------------------------------------------


def test_masker_redacts_all_sensitive_kinds() -> None:
    masker = SensitiveDataMasker()
    raw = "contact budi@mail.com or 081234567890 rekening 1234567890123456"

    result = masker.mask(raw)

    assert result.masked_kinds == ("account", "email", "phone")
    assert result.masked_count == 3
    assert "budi@mail.com" not in result.masked_text
    assert "081234567890" not in result.masked_text
    assert "1234567890123456" not in result.masked_text
    assert "[MASKED:email:" in result.masked_text


def test_masker_is_deterministic_for_correlation() -> None:
    masker = SensitiveDataMasker()

    first = masker.mask("budi@mail.com")
    second = masker.mask("budi@mail.com")

    assert first.correlation_reference == second.correlation_reference
    assert first.masked_text == second.masked_text


# --- Masking boundary proof -----------------------------------------------------


def test_declared_amount_is_masked_before_crossing_the_boundary() -> None:
    extractor, stub = _extractor(
        structured=lambda _messages: _valid_output()
    )
    sensitive_amount = Decimal("1234567890123")  # account-like digit run

    extractor.extract(
        receipt=_receipt(),
        content=_jpeg_bytes(),
        declared_amount=sensitive_amount,
        attempt=1,
    )

    prompt_text = stub.calls[0][0].content[0]["text"]
    assert "[MASKED:account:" in prompt_text
    assert "1234567890123" not in prompt_text


def test_prompt_carries_no_employee_identifiers() -> None:
    extractor, stub = _extractor(structured=lambda _m: _valid_output())

    extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(), declared_amount=None, attempt=1
    )

    prompt_text = stub.calls[0][0].content[0]["text"]
    assert "employee" not in prompt_text.lower()
    assert stub.calls[0][0].content[1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )


# --- Image envelope sanitization (FR-13, image privacy design) ----------------


def _outgoing_image_bytes(stub: StubStructured) -> bytes:
    import base64

    data_uri = stub.calls[0][0].content[1]["image_url"]["url"]
    return base64.b64decode(data_uri.split(",", 1)[1])


def test_outgoing_image_metadata_is_stripped_at_the_boundary() -> None:
    extractor, stub = _extractor(structured=lambda _m: _valid_output())

    extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(), declared_amount=None, attempt=1
    )

    image = _outgoing_image_bytes(stub)
    assert b"Exif" not in image
    assert b"GPS" not in image
    assert b"Device:PhoneX" not in image
    assert b"handwritten-note" not in image  # COM comment
    assert b"CATEGORY:MEALS" not in image  # marker rides the stripped COM
    assert image.startswith(b"\xff\xd8")
    assert Image.open(BytesIO(image)).size == (4, 4)  # pixels survive, decodable


def test_outgoing_png_text_chunks_are_stripped_at_the_boundary() -> None:
    extractor, stub = _extractor(structured=lambda _m: _valid_output())

    extractor.extract(
        receipt=_receipt("image/png"),
        content=_png_bytes(),
        declared_amount=None,
        attempt=1,
    )

    image = _outgoing_image_bytes(stub)
    assert b"SECRET-GPS-DATA" not in image
    assert Image.open(BytesIO(image)).size == (4, 4)  # critical chunks survive


@pytest.mark.parametrize(
    "content",
    [
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", b"\x00" * 13)
        + _png_chunk(b"IEND", b""),  # no IDAT: no image data
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"tEXt", b"Comment\x00x")
        + _png_chunk(b"IHDR", b"\x00" * 13)
        + _png_chunk(b"IDAT", b"pixels")
        + _png_chunk(b"IEND", b""),  # IHDR is not the first chunk
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", b"\x00" * 13)
        + _png_chunk_with_crc(b"IDAT", b"pixels", 0xDEADBEEF)
        + _png_chunk(b"IEND", b""),  # corrupt chunk CRC
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", b"\x00" * 13)
        + _png_chunk(b"IDAT", b"pixels")
        + _png_chunk(b"IEND", b"")
        + b"trailing-junk",  # payload after IEND
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(
            b"IHDR", b"\x00\x00\x00\x04\x00\x00\x00\x04\x08\x00\x00\x00\x00"
        )
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x01\x02short-scan"))
        + _png_chunk(b"IEND", b""),  # valid CRCs but the scan cannot decode
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(
            b"IHDR", b"\x00\x00\x27\x10\x00\x00\x27\x10\x08\x00\x00\x00\x00"
        )
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + _png_chunk(b"IEND", b""),  # 10000x10000 exceeds the pixel guard
    ],
    ids=[
        "no-idat",
        "ihdr-not-first",
        "corrupt-crc",
        "trailing-after-iend",
        "undecodable-scan",
        "dimension-bomb",
    ],
)
def test_corrupt_pngs_fail_closed(content) -> None:
    extractor, stub = _extractor(
        _settings(provider_fallback="none"), structured=lambda _m: _valid_output()
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt("image/png"),
            content=content,
            declared_amount=None,
            attempt=1,
        )

    assert excinfo.value.code == "image_sanitization_failed"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert stub.calls == []


def test_unparseable_image_fails_closed_without_a_provider_call() -> None:
    extractor, stub = _extractor(
        _settings(provider_fallback="none"), structured=lambda _m: _valid_output()
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(),
            content=b"\xff\xd8\xffbogus",
            declared_amount=None,
            attempt=1,
        )

    assert excinfo.value.code == "image_sanitization_failed"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert stub.calls == [], "corrupt image must never reach the provider"


def test_jpeg_bytes_after_end_of_image_are_discarded() -> None:
    extractor, stub = _extractor(structured=lambda _m: _valid_output())

    trailing = _jpeg_bytes() + b"SMUGGLED-TRAILING-PAYLOAD"
    extractor.extract(
        receipt=_receipt(), content=trailing, declared_amount=None, attempt=1
    )

    image = _outgoing_image_bytes(stub)
    assert b"SMUGGLED-TRAILING-PAYLOAD" not in image
    assert image.endswith(b"\xff\xd9"), "output must stop at end-of-image"
    assert Image.open(BytesIO(image)).size == (4, 4), "legitimate pixels survive"


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xd8"
        + _jpeg_segment(b"\xff\xe0", b"JFIF\x00" + b"\x00" * 9)
        + b"\xff",  # ends on a lone marker byte
        b"\xff\xd8" + b"\xff\xda\x00\x02" + b"entropy-without-eoi",  # no EOI
    ],
    ids=["lone-marker-byte", "scan-without-eoi"],
)
def test_truncated_jpegs_fail_closed_as_sanitization_errors(content) -> None:
    extractor, stub = _extractor(
        _settings(provider_fallback="none"), structured=lambda _m: _valid_output()
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=content, declared_amount=None, attempt=1
        )

    assert excinfo.value.code == "image_sanitization_failed"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert stub.calls == []


# --- Error taxonomy ---------------------------------------------------------------


def test_malformed_model_output_is_non_retryable() -> None:
    def bad_output(_messages):
        # Violates the contract (negative total) -> ValidationError inside.
        return {"vendor": "x", "receipt_date": "2026-10-04", "total": "-5",
                "currency": "IDR", "category": "meals", "confidence": "0.9"}

    extractor, _ = _extractor(
        _settings(provider_fallback="none"), structured=bad_output
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"
    assert (
        excinfo.value.details["classification"]
        == ErrorClassification.NON_RETRYABLE
    )


def test_provider_outage_is_retryable_and_bounded() -> None:
    calls = {"count": 0}

    def always_down(_messages):
        calls["count"] += 1
        raise RuntimeError("connection refused")

    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=2),
        structured=always_down,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "provider_unavailable"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.RETRYABLE
    )
    assert calls["count"] == 3, "initial attempt + 2 bounded retries"


def test_fallback_mode_degrades_to_mock_with_marked_provider() -> None:
    def always_down(_messages):
        raise RuntimeError("connection refused")

    extractor, _ = _extractor(
        _settings(provider_fallback="mock", llm_max_retries=0),
        structured=always_down,
    )

    result = extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(),
        declared_amount=Decimal("60000"), attempt=1,
    )

    assert result.provider.startswith("llm-fallback-mock:")
    assert "live_provider_unavailable" in result.warnings
    assert result.provider_degraded is True


def test_pdf_receipt_degrades_to_mock_only_in_fallback_mode() -> None:
    extractor, stub = _extractor(
        _settings(provider_fallback="mock", llm_max_retries=0),
        structured=lambda _m: _valid_output(),
    )

    result = extractor.extract(
        receipt=_receipt("application/pdf"),
        content=b"%PDF-1.7\nfallback\n%%EOF",
        declared_amount=Decimal("60000"),
        attempt=1,
    )

    assert result.provider.startswith("llm-fallback-mock:")
    assert stub.calls == [], "unsupported media must never reach the provider"


def test_langchain_parse_error_is_non_retryable_and_never_retried() -> None:
    calls = {"count": 0}

    def unparseable(_messages):
        calls["count"] += 1
        raise OutputParserException("Failed to parse completion as JSON")

    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=3),
        structured=unparseable,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert calls["count"] == 1, "parse failures must not be retried"


def test_fallback_never_masks_langchain_parse_errors() -> None:
    def unparseable(_messages):
        raise OutputParserException("Failed to parse completion as JSON")

    extractor, _ = _extractor(
        _settings(provider_fallback="mock", llm_max_retries=0),
        structured=unparseable,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"


def test_error_details_never_carry_raw_output_text() -> None:
    def unparseable(_messages):
        raise OutputParserException("RAW-MODEL-RESPONSE vendor+receipt text")

    extractor, _ = _extractor(
        _settings(provider_fallback="none"), structured=unparseable
    )
    with pytest.raises(ApplicationError) as parse_error:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )
    assert "RAW-MODEL-RESPONSE" not in str(parse_error.value.details)
    assert parse_error.value.details["exception_type"] == "OutputParserException"

    def bad_output(_messages):
        return {"vendor": "x", "receipt_date": "2026-10-04", "total": "-5",
                "currency": "IDR", "category": "meals", "confidence": "0.9"}

    validator, _ = _extractor(
        _settings(provider_fallback="none"), structured=bad_output
    )
    with pytest.raises(ApplicationError) as validation_error:
        validator.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )
    assert "-5" not in str(validation_error.value.details)


# --- Image privacy gate (pixel disclosure control) -----------------------------------


def test_block_mode_keeps_image_bytes_inside_the_boundary() -> None:
    extractor, stub = _extractor(
        _settings(llm_image_privacy_mode="block", provider_fallback="none"),
        structured=lambda _m: _valid_output(),
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "image_privacy_blocked"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert stub.calls == [], "blocked images must never reach the provider"


def test_block_mode_with_fallback_routes_to_the_local_mock() -> None:
    extractor, stub = _extractor(
        _settings(llm_image_privacy_mode="block", provider_fallback="mock"),
        structured=lambda _m: _valid_output(),
    )

    result = extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(),
        declared_amount=Decimal("60000"), attempt=1,
    )

    assert result.provider.startswith("llm-fallback-mock:")
    assert result.provider_degraded is True
    assert stub.calls == [], "the provider must not receive blocked images"


def test_send_mode_still_masks_text_and_strips_metadata() -> None:
    extractor, stub = _extractor(
        _settings(llm_image_privacy_mode="send"),
        structured=lambda _m: _valid_output(),
    )

    extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(),
        declared_amount=Decimal("1234567890123"), attempt=1,
    )

    prompt_text = stub.calls[0][0].content[0]["text"]
    assert "[MASKED:account:" in prompt_text
    image = _outgoing_image_bytes(stub)
    assert b"Exif" not in image and b"GPS" not in image


def test_fallback_never_masks_malformed_model_output() -> None:
    def bad_output(_messages):
        return {"vendor": "x", "receipt_date": "2026-10-04", "total": "-5",
                "currency": "IDR", "category": "meals", "confidence": "0.9"}

    extractor, _ = _extractor(
        _settings(provider_fallback="mock"), structured=bad_output
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )


def test_fallback_never_masks_configuration_failures() -> None:
    def unauthorized(_messages):
        raise _provider_status_error(openai.AuthenticationError, 401)

    extractor, _ = _extractor(
        _settings(provider_fallback="mock", llm_max_retries=0),
        structured=unauthorized,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "provider_authentication_failed"


def test_fallback_never_masks_sanitization_failures() -> None:
    extractor, _ = _extractor(
        _settings(provider_fallback="mock"), structured=lambda _m: _valid_output()
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=b"\xff\xd8\xffbogus",
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "image_sanitization_failed"


def test_fallback_after_live_failure_never_auto_approves() -> None:
    def always_down(_messages):
        raise RuntimeError("connection refused")

    extractor = LlmReceiptExtractor(
        _settings(provider_fallback="mock", llm_max_retries=0),
        SensitiveDataMasker(),
    )
    extractor._structured = StubStructured(always_down)
    app.dependency_overrides[get_receipt_extractor] = lambda: extractor
    try:
        created = client.post(
            "/claims",
            data={"employee_id": "fallback-e2e", "declared_amount": "60000"},
            files={"files": ("receipt.jpg", BytesIO(_jpeg_bytes()), "image/jpeg")},
        )
        assert created.status_code == 201, created.text
        claim_id = created.json()["claim"]["id"]

        processed = client.post(f"/claims/{claim_id}/process")
        assert processed.status_code == 200, processed.text
        payload = processed.json()

        assert payload["decision"]["outcome"] == "escalated"
        assert "provider_fallback_active" in payload["decision"]["reason_codes"]

        detail = client.get(f"/claims/{claim_id}").json()
        degraded = [
            signal
            for signal in detail["signals"]
            if signal["signal_type"] == "provider_degraded"
        ]
        assert degraded, "fallback provenance must be visible as a signal"
    finally:
        app.dependency_overrides.pop(get_receipt_extractor, None)


def test_pdf_receipt_in_live_mode_is_classified_without_fallback() -> None:
    extractor, _ = _extractor(
        _settings(provider_fallback="none"),
        structured=lambda _m: _valid_output(),
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt("application/pdf"),
            content=b"%PDF-1.7\nx\n%%EOF",
            declared_amount=None,
            attempt=1,
        )

    assert excinfo.value.code == "unsupported_media_for_vision"
    assert excinfo.value.status_code == 415


# --- Provider error classification -------------------------------------------------


def _provider_status_error(cls, status: int) -> Exception:
    request = httpx.Request("POST", "https://provider.test/v1/chat/completions")
    return cls("provider said no", response=httpx.Response(status, request=request), body=None)


def _provider_connection_error(cls) -> Exception:
    return cls(request=httpx.Request("POST", "https://provider.test"))


def test_provider_timeout_is_retryable_and_bounded() -> None:
    calls = {"count": 0}

    def always_timeout(_messages):
        calls["count"] += 1
        raise _provider_connection_error(openai.APITimeoutError)

    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=1),
        structured=always_timeout,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "provider_timeout"
    assert excinfo.value.status_code == 504
    assert excinfo.value.details["classification"] == ErrorClassification.RETRYABLE
    assert calls["count"] == 2, "initial attempt + 1 bounded retry"


def test_provider_rate_limit_is_retryable() -> None:
    def always_limited(_messages):
        raise _provider_status_error(openai.RateLimitError, 429)

    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=0),
        structured=always_limited,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "provider_rate_limited"
    assert excinfo.value.details["classification"] == ErrorClassification.RETRYABLE


@pytest.mark.parametrize(
    ("exception_factory", "expected_code"),
    [
        (
            lambda: _provider_status_error(openai.AuthenticationError, 401),
            "provider_authentication_failed",
        ),
        (
            lambda: _provider_status_error(openai.BadRequestError, 400),
            "provider_invalid_request",
        ),
        (
            lambda: _provider_status_error(openai.NotFoundError, 404),
            "provider_unsupported_configuration",
        ),
    ],
    ids=["auth", "invalid-request", "unsupported-config"],
)
def test_provider_config_errors_are_non_retryable_and_never_retried(
    exception_factory, expected_code
) -> None:
    calls = {"count": 0}

    def failing(_messages):
        calls["count"] += 1
        raise exception_factory()

    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=3),
        structured=failing,
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == expected_code
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert calls["count"] == 1, "configuration errors must not be retried"


def test_unknown_provider_failure_stays_retryable_as_unavailable() -> None:
    extractor, _ = _extractor(
        _settings(provider_fallback="none", llm_max_retries=0),
        structured=lambda _m: (_ for _ in ()).throw(ValueError("surprise")),
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "provider_unavailable"
    assert excinfo.value.details["error_type"] == "ValueError"
    assert excinfo.value.details["classification"] == ErrorClassification.RETRYABLE


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xd8\xff\xd9",  # bare SOI+EOI: no frame, no scan
        b"\xff\xd8"
        + _jpeg_segment(b"\xff\xe0", b"JFIF\x00" + b"\x00" * 9)
        + b"\xff\xd9",  # markers only, still no image data
    ],
    ids=["soi-eoi-only", "markers-without-frame"],
)
def test_jpeg_without_frame_or_scan_fails_closed(content) -> None:
    extractor, stub = _extractor(
        _settings(provider_fallback="none"), structured=lambda _m: _valid_output()
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=content, declared_amount=None, attempt=1
        )

    assert excinfo.value.code == "image_sanitization_failed"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )
    assert stub.calls == []


# --- Result contract (LLM output -> ExtractionResult) -------------------------------


def test_line_item_unit_price_never_rounds_to_zero() -> None:
    extractor, _ = _extractor(
        structured=lambda _m: _valid_output().model_copy(
            update={"total": Decimal("0.01"), "quantity": Decimal("1000")}
        )
    )

    result = extractor.extract(
        receipt=_receipt(), content=_jpeg_bytes(), declared_amount=None, attempt=1
    )

    unit_price = result.line_items[0].unit_price
    assert unit_price > 0, "rounding must not collapse the unit price"
    assert result.total.value == Decimal("0.01")


def test_degenerate_line_item_is_classified_malformed() -> None:
    extractor, _ = _extractor(
        structured=lambda _m: _valid_output().model_copy(
            update={"total": Decimal("1E-30"), "quantity": Decimal("1E30")}
        )
    )

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )


def test_result_schema_violation_is_classified_malformed(monkeypatch) -> None:
    from app.integrations import llm as llm_module

    class ImpossibleTotalItem(BaseModel):
        description: str = Field(min_length=1, max_length=255)
        quantity: Decimal = Field(gt=0)
        unit_price: Decimal = Field(gt=0)
        total: Decimal = Field(gt=1000000)  # unreachable for the test total

    monkeypatch.setattr(llm_module, "ExtractedLineItem", ImpossibleTotalItem)
    extractor, _ = _extractor(structured=lambda _m: _valid_output())

    with pytest.raises(ApplicationError) as excinfo:
        extractor.extract(
            receipt=_receipt(), content=_jpeg_bytes(),
            declared_amount=None, attempt=1,
        )

    assert excinfo.value.code == "malformed_extraction"
    assert (
        excinfo.value.details["classification"] == ErrorClassification.NON_RETRYABLE
    )


# --- Dependency wiring --------------------------------------------------------------


def test_provider_mode_selects_the_extractor() -> None:
    assert isinstance(
        get_receipt_extractor(Settings(_env_file=None, provider_mode="mock")),
        MockReceiptExtractor,
    )
    assert isinstance(
        get_receipt_extractor(_settings()),
        LlmReceiptExtractor,
    )


def test_live_mode_without_api_key_fails_fast() -> None:
    with pytest.raises(RuntimeError):
        get_receipt_extractor(Settings(_env_file=None, provider_mode="live"))


def test_masker_dependency_is_available() -> None:
    assert isinstance(get_sensitive_data_masker(), SensitiveDataMasker)
