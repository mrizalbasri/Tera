from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.domain.enums import ClaimStatus, Severity
from app.errors import ApplicationError
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.main import app
from app.schemas.core import (
    Claim,
    ExtractedLineItem,
    ExtractionResult,
    FieldConfidence,
)
from app.services.validation import ValidationService

client = TestClient(app)
VALIDATION = ValidationService(Settings(_env_file=None))
RETRIEVER = LocalPolicyRetriever()
EVALUATOR = LocalPolicyEvaluator()


def _claim(declared: str = "60000") -> Claim:
    now = datetime.now(UTC)
    return Claim(
        id=uuid4(),
        employee_id="validation-test",
        status=ClaimStatus.RECEIVED,
        submitted_at=now,
        currency="IDR",
        declared_amount=Decimal(declared),
        created_at=now,
        updated_at=now,
    )


def _extraction(
    *,
    total: str = "60000",
    category: str = "meals",
    receipt_date: date | None = None,
    line_total: str | None = None,
    currency: str = "IDR",
) -> ExtractionResult:
    day = receipt_date if receipt_date is not None else date.today() - timedelta(days=1)
    item_total = Decimal(line_total if line_total is not None else total)
    return ExtractionResult(
        id=uuid4(),
        receipt_id=uuid4(),
        processing_run_id=uuid4(),
        vendor=FieldConfidence(value="Synthetic Vendor", confidence=Decimal("0.96")),
        receipt_date=FieldConfidence(value=day, confidence=Decimal("0.96")),
        total=FieldConfidence(value=Decimal(total), confidence=Decimal("0.96")),
        currency=FieldConfidence(value=currency, confidence=Decimal("0.96")),
        category=FieldConfidence(value=category, confidence=Decimal("0.96")),
        line_items=[
            ExtractedLineItem(
                description="Synthetic expense",
                quantity=Decimal("1"),
                unit_price=item_total,
                total=item_total,
            )
        ],
        provider="unit-test",
        created_at=datetime.now(UTC),
    )


def _finding(findings, rule_id):
    for finding in findings:
        key = finding.rule_id if hasattr(finding, "rule_id") else finding["rule_id"]
        if key == rule_id:
            return finding
    raise AssertionError(f"finding '{rule_id}' not found in {findings}")


def test_valid_extraction_passes_all_validation_rules() -> None:
    findings = VALIDATION.validate(claim=_claim(), extraction=_extraction(), processing_run_id=uuid4())

    assert findings, "expected findings to be recorded"
    assert all(finding.passed for finding in findings), [
        finding.rule_id for finding in findings if not finding.passed
    ]


def test_future_receipt_date_is_blocking() -> None:
    extraction = _extraction(receipt_date=date.today() + timedelta(days=1))

    finding = _finding(
        VALIDATION.validate(claim=_claim(), extraction=extraction, processing_run_id=uuid4()),
        "receipt_date_not_in_future",
    )

    assert not finding.passed
    assert finding.severity == Severity.BLOCKING
    assert finding.reason_code == "receipt_date_in_future"


def test_expired_receipt_is_blocking() -> None:
    extraction = _extraction(receipt_date=date.today() - timedelta(days=20))

    finding = _finding(
        VALIDATION.validate(claim=_claim(), extraction=extraction, processing_run_id=uuid4()),
        "receipt_within_claim_window",
    )

    assert not finding.passed
    assert finding.reason_code == "receipt_too_old"


def test_line_item_mismatch_is_blocking() -> None:
    extraction = _extraction(total="60000", line_total="30000")

    finding = _finding(
        VALIDATION.validate(claim=_claim(), extraction=extraction, processing_run_id=uuid4()),
        "total_matches_line_items",
    )

    assert not finding.passed
    assert finding.reason_code == "total_line_item_mismatch"


def test_unknown_category_is_blocking() -> None:
    extraction = _extraction(category="unknown_category")

    finding = _finding(
        VALIDATION.validate(claim=_claim(), extraction=extraction, processing_run_id=uuid4()),
        "category_supported",
    )

    assert not finding.passed
    assert finding.reason_code == "unsupported_category"


def test_currency_mismatch_is_a_warning() -> None:
    extraction = _extraction(currency="USD")

    finding = _finding(
        VALIDATION.validate(claim=_claim(), extraction=extraction, processing_run_id=uuid4()),
        "currency_matches_claim",
    )

    assert not finding.passed
    assert finding.severity == Severity.WARNING


def test_policy_retrieval_selects_versioned_record() -> None:
    policy = RETRIEVER.retrieve(category="meals", effective_date=date.today())

    assert policy.policy_id == "expense-policy"
    assert policy.version == 1
    rule_ids = {rule.rule_id for rule in policy.rules}
    assert {"meal_daily_limit", "receipt_required", "prohibited_items"} <= rule_ids


def test_policy_retrieval_fails_explicitly_for_unknown_category() -> None:
    with pytest.raises(ApplicationError) as excinfo:
        RETRIEVER.retrieve(category="crypto", effective_date=date.today())

    assert excinfo.value.code == "policy_unavailable"


def test_policy_retrieval_fails_before_effective_date() -> None:
    with pytest.raises(ApplicationError) as excinfo:
        RETRIEVER.retrieve(category="meals", effective_date=date(2025, 1, 1))

    assert excinfo.value.code == "policy_unavailable"


def test_over_limit_meal_fails_policy_evaluation() -> None:
    claim = _claim(declared="240000")
    extraction = _extraction(total="240000", category="meals")
    policy = RETRIEVER.retrieve(category="meals", effective_date=date.today())

    evaluations = EVALUATOR.evaluate(
        claim=claim, extraction=extraction, policy=policy, processing_run_id=uuid4()
    )

    meal = next(e for e in evaluations if e.rule_id == "meal_daily_limit")
    assert not meal.passed
    assert meal.severity == Severity.BLOCKING
    assert meal.reason_code == "policy_limit_exceeded"
    assert meal.policy_version == 1


def test_alcohol_line_item_fails_prohibited_rule() -> None:
    claim = _claim()
    extraction = _extraction(category="meals")
    extraction = extraction.model_copy(
        update={
            "line_items": [
                ExtractedLineItem(
                    description="Cold alcohol beer",
                    quantity=Decimal("1"),
                    unit_price=Decimal("60000"),
                    total=Decimal("60000"),
                )
            ]
        }
    )
    policy = RETRIEVER.retrieve(category="meals", effective_date=date.today())

    evaluations = EVALUATOR.evaluate(
        claim=claim, extraction=extraction, policy=policy, processing_run_id=uuid4()
    )

    prohibited = next(e for e in evaluations if e.rule_id == "prohibited_items")
    assert not prohibited.passed
    assert prohibited.reason_code == "prohibited_item"


def _create_claim(content: bytes, declared: str = "60000") -> str:
    response = client.post(
        "/claims",
        data={"employee_id": "policy-test", "declared_amount": declared},
        files={"files": ("receipt.pdf", _bytes_io(content), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["claim"]["id"]


def _bytes_io(content: bytes):
    from io import BytesIO

    return BytesIO(content)


def test_pipeline_records_validation_and_policy_results() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nCATEGORY:MEALS TOTAL_MISMATCH\n%%EOF")

    response = client.post(f"/claims/{claim_id}/process")

    assert response.status_code == 200
    payload = response.json()
    finding = _finding(payload["validation_findings"], "total_matches_line_items")
    assert finding["passed"] is False
    assert finding["reason_code"] == "total_line_item_mismatch"


def test_over_limit_meal_claim_is_flagged_by_policy() -> None:
    claim_id = _create_claim(
        b"%PDF-1.7\nCATEGORY:MEALS over-limit\n%%EOF", declared="240000"
    )

    payload = client.post(f"/claims/{claim_id}/process").json()

    meal = _finding(payload["policy_evaluations"], "meal_daily_limit")
    assert meal["passed"] is False
    assert meal["reason_code"] == "policy_limit_exceeded"
    assert payload["claim"]["status"] == "rejected"
    assert payload["decision"]["outcome"] == "rejected"


def test_alcohol_receipt_fails_policy_in_pipeline() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nCATEGORY:MEALS ALCOHOL\n%%EOF")

    payload = client.post(f"/claims/{claim_id}/process").json()

    prohibited = _finding(payload["policy_evaluations"], "prohibited_items")
    assert prohibited["passed"] is False
    assert prohibited["reason_code"] == "prohibited_item"


def test_old_receipt_is_flagged_by_validation_in_pipeline() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nCATEGORY:MEALS OLD_DATE\n%%EOF")

    payload = client.post(f"/claims/{claim_id}/process").json()

    finding = _finding(payload["validation_findings"], "receipt_within_claim_window")
    assert finding["passed"] is False
    assert finding["reason_code"] == "receipt_too_old"


def test_successful_replay_includes_validation_and_policy_results() -> None:
    claim_id = _create_claim(b"%PDF-1.7\nCATEGORY:MEALS replay-check\n%%EOF")

    first = client.post(f"/claims/{claim_id}/process")
    second = client.post(f"/claims/{claim_id}/process")

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert first.json()["policy_evaluations"]
