"""M7 tests: masking boundary (FR-13), LangChain adapter, error taxonomy."""

from decimal import Decimal
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

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
        content=b"\xff\xd8\xffimage",
        declared_amount=sensitive_amount,
        attempt=1,
    )

    prompt_text = stub.calls[0][0].content[0]["text"]
    assert "[MASKED:account:" in prompt_text
    assert "1234567890123" not in prompt_text


def test_prompt_carries_no_employee_identifiers() -> None:
    extractor, stub = _extractor(structured=lambda _m: _valid_output())

    extractor.extract(
        receipt=_receipt(), content=b"\xff\xd8\xffimage", declared_amount=None, attempt=1
    )

    prompt_text = stub.calls[0][0].content[0]["text"]
    assert "employee" not in prompt_text.lower()
    assert stub.calls[0][0].content[1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )


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
            receipt=_receipt(), content=b"\xff\xd8\xffimage",
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
            receipt=_receipt(), content=b"\xff\xd8\xffimage",
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
        receipt=_receipt(), content=b"%PDF-1.7\nfallback\n%%EOF",
        declared_amount=Decimal("60000"), attempt=1,
    )

    assert result.provider.startswith("llm-fallback-mock:")
    assert "live_provider_unavailable" in result.warnings


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
