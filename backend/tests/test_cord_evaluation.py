from decimal import Decimal

import pytest

from scripts.evaluate_cord import TextInput, amount_candidates, parse_amount, summarize


@pytest.mark.parametrize("raw,expected", [
    ("Rp. 91,000", "91000"), ("Rp.118.000", "118000"),
    ("63,000.00", "63000"), ("9.500,00", "9500"),
    ("60.000", "60000"), ("91000", "91000"), ("1,200,000", "1200000"),
])
def test_cord_total_formats(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


def test_unavailable_provider_is_not_reported_as_measured_accuracy():
    summary = summarize([{"status": "error", "error_code": "provider_unavailable",
                          "expected_total": "60000", "duration_seconds": 1.0}])
    assert summary["exact_total_rate_including_failures"] is None
    assert summary["errors"] == {"provider_unavailable": 1}


def test_missing_total_label_is_excluded_but_failed_labeled_case_counts():
    summary = summarize([
        {"status": "success", "expected_total": "60000", "total_exact_match": True,
         "duration_seconds": 1.0, "receipt_date": None},
        {"status": "success", "expected_total": None, "total_exact_match": None,
         "duration_seconds": 1.0, "receipt_date": None},
        {"status": "error", "expected_total": "20000", "error_code": "provider_timeout",
         "duration_seconds": 30.0},
    ])
    assert summary["total_label_available"] == 2
    assert summary["missing_total_labels"] == 1
    assert summary["exact_total_rate_including_failures"] == 0.5


def test_text_mode_sends_masked_ocr_text_without_receipt_image():
    class Capture:
        messages = None

        def invoke(self, messages):
            self.messages = messages
            return {"total": "60000"}

    capture = Capture()
    adapted = TextInput(capture, "TOTAL 60000 contact synthetic@example.test")
    assert adapted.invoke(["data:image/png;base64,PRIVATE_IMAGE"]) == {"total": "60000"}
    content = capture.messages[0].content
    assert isinstance(content, str)
    assert "TOTAL 60000" in content
    assert "synthetic@example.test" not in content
    assert "PRIVATE_IMAGE" not in content
    assert "[MASKED:email:" in content


def test_text_mode_supplies_normalized_grouped_amounts_without_changing_source():
    class Capture:
        messages = None

        def invoke(self, messages):
            self.messages = messages
            return {"total": "16000"}

    capture = Capture()
    raw = "SINGLE SCOOP\n16.000\nTOTAL\n16.000\nCASH\n50.000\nCHANGE\n34.000"
    adapted = TextInput(capture, raw)
    assert adapted.invoke([])["total"] == "16000"
    content = capture.messages[0].content
    assert raw in content
    assert '"normalized": "16000"' in content
    assert '"normalized": "50000"' in content
    assert '"normalized": "34000"' in content


@pytest.mark.parametrize("wrong_total", ["16", "16.000", 16, Decimal("16.000")])
def test_text_mode_rejects_decimal_misinterpretation_instead_of_scaling_guess(wrong_total):
    from app.errors import ApplicationError

    class WrongTotal:
        def invoke(self, messages):
            return {"total": wrong_total}

    with pytest.raises(ApplicationError) as error:
        TextInput(WrongTotal(), "TOTAL\n16.000\nCASH\n50.000\nCHANGE\n34.000").invoke([])
    assert error.value.code == "malformed_extraction"
    assert error.value.details["stage"] == "ocr_amount_grounding"


def test_ocr_amount_candidates_support_currency_prefix_and_spacing():
    candidates = amount_candidates("TOTAL RP38. 000\nCASH Rp50.000\nCHANGE RP12.000")
    assert {c["normalized"] for c in candidates} == {"38000", "50000", "12000"}


def test_ocr_amount_candidates_do_not_turn_dates_or_alphanumeric_ids_into_money():
    assert amount_candidates("2026-10-17\nREF12345\n[masked:email:abc123]") == []


def test_text_mode_checks_parsed_model_output_as_well_as_dicts():
    from app.errors import ApplicationError
    from app.integrations.llm import LlmExtractionOutput

    parsed = LlmExtractionOutput(vendor=None, receipt_date=None, total="16.000",
                                 currency="IDR", category="other", confidence="0.8")
    assert parsed.total == Decimal("16")

    class WrongParsedTotal:
        def invoke(self, messages):
            return parsed

    with pytest.raises(ApplicationError) as error:
        TextInput(WrongParsedTotal(), "TOTAL\n16.000").invoke([])
    assert error.value.details["stage"] == "ocr_amount_grounding"


@pytest.mark.parametrize("text", [
    "SUBTOTAL\n238,000\nTOTAL\n281-435\nCASH\n300,000",
    "2 DONUT\n18,000\n1 BREAD\n11,000\n1 CAKE\n13,000\n1 ROLL\n12,000\nTOTAL\n52,000",
    "SUB TOTAL\n17,000\nGRAND TOTAL\n22,000\nCASHIDR\n5,000\nCHANGE DUE",
])
def test_hybrid_reads_image_when_ocr_total_evidence_is_inconsistent(text):
    from scripts.evaluate_cord import HybridInput

    class Capture:
        calls = []

        def invoke(self, messages):
            self.calls.append(messages)
            return {"total": "12345"}

    capture = Capture()
    adapted = HybridInput(capture, text)
    image_messages = ["sanitized-image-message"]
    assert adapted.invoke(image_messages) == {"total": "12345"}
    assert capture.calls == [image_messages]
    assert adapted.route == "vision"
    assert adapted.reasons


def test_hybrid_keeps_consistent_ocr_text_only():
    from scripts.evaluate_cord import HybridInput

    class Capture:
        calls = []

        def invoke(self, messages):
            self.calls.append(messages)
            return {"total": "16000"}

    capture = Capture()
    adapted = HybridInput(capture, "TOTAL\n16.000\nCASH\n50.000\nCHANGE\n34.000")
    assert adapted.invoke(["image"]) == {"total": "16000"}
    assert adapted.route == "text"
    assert len(capture.calls) == 1
    assert "image" not in capture.calls[0]


def test_hybrid_rechecks_image_when_model_selects_cash_instead_of_total():
    from scripts.evaluate_cord import HybridInput

    class Capture:
        def __init__(self):
            self.calls = []

        def invoke(self, messages):
            self.calls.append(messages)
            return {"total": "50000" if len(self.calls) == 1 else "16000"}

    capture = Capture()
    adapted = HybridInput(capture, "TOTAL\n16.000\nCASH\n50.000\nCHANGE\n34.000")
    image_messages = ["sanitized-image-message"]
    assert adapted.invoke(image_messages)["total"] == "16000"
    assert len(capture.calls) == 2
    assert capture.calls[1] == image_messages
    assert adapted.reasons == ["output_disagrees_with_total_label"]


def test_hybrid_does_not_retry_provider_timeout_with_an_image():
    from app.errors import ApplicationError
    from scripts.evaluate_cord import HybridInput

    class Unavailable:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            raise ApplicationError("provider_timeout", "Provider timed out", 502)

    provider = Unavailable()
    with pytest.raises(ApplicationError):
        HybridInput(provider, "TOTAL\n16.000").invoke(["image"])
    assert provider.calls == 1


def test_hybrid_does_not_replace_total_with_item_sum_when_discount_exists():
    from scripts.evaluate_cord import ocr_total_evidence

    reasons, totals = ocr_total_evidence("1 CAKE\n20,000\n1 DRINK\n10,000\nDISCOUNT\n5,000\nTOTAL\n25,000")
    assert reasons == []
    assert totals == {Decimal("25000")}
