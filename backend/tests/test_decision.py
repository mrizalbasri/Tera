from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import (
    ClaimStatus,
    DuplicateMatchType,
    Severity,
    SignalType,
)
from app.main import app
from app.schemas.core import (
    Claim,
    PolicyEvaluation,
    Signal,
    ValidationFinding,
)
from app.services.decision import DecisionEngine

client = TestClient(app)
ENGINE = DecisionEngine(Settings(_env_file=None))


def _process(content: bytes, declared: str, employee: str = "decision-test") -> dict:
    created = client.post(
        "/claims",
        data={"employee_id": employee, "declared_amount": declared},
        files={"files": ("receipt.pdf", BytesIO(content), "application/pdf")},
    )
    assert created.status_code == 201, created.text
    claim_id = created.json()["claim"]["id"]
    response = client.post(f"/claims/{claim_id}/process")
    assert response.status_code == 200, response.text
    return response.json()


def test_valid_meal_claim_is_auto_approved() -> None:
    payload = _process(
        b"%PDF-1.7\nCATEGORY:MEALS valid-meal\n%%EOF", declared="60000"
    )

    assert payload["decision"]["outcome"] == "approved"
    assert "within_policy" in payload["decision"]["reason_codes"]
    assert payload["decision"]["created_by"] == "agent"
    assert payload["claim"]["status"] == "approved"
    assert payload["decision"]["id"] == payload["claim"]["current_decision_id"]


def test_identical_attributes_are_rejected_as_duplicate() -> None:
    first = _process(b"%PDF-1.7\nfirst-parking\n%%EOF", declared="60000")
    assert first["decision"]["outcome"] == "approved"

    second = _process(b"%PDF-1.7\nsecond-parking-copy\n%%EOF", declared="60000")

    assert second["decision"]["outcome"] == "rejected"
    assert second["decision"]["reason_codes"] == ["duplicate_receipt"]
    assert second["decision"]["source_signal_ids"]
    assert second["claim"]["status"] == "rejected"

    detail = client.get(f"/claims/{second['claim']['id']}").json()
    duplicate_signals = [
        signal
        for signal in detail["signals"]
        if signal["signal_type"] == "duplicate"
    ]
    assert duplicate_signals
    assert duplicate_signals[0]["compared_fields"] == [
        "vendor",
        "receipt_date",
        "total",
    ]
    assert duplicate_signals[0]["matched_claim_ids"] == [first["claim"]["id"]]


def test_claim_above_escalation_amount_is_escalated() -> None:
    payload = _process(b"%PDF-1.7\nlarge-claim\n%%EOF", declared="700000")

    assert payload["decision"]["outcome"] == "escalated"
    assert "escalation_amount_threshold" in payload["decision"]["reason_codes"]
    assert payload["claim"]["status"] == "escalated"


def test_unusual_spending_pattern_is_flagged_as_anomaly() -> None:
    # Distinct amounts so the duplicate detector does not reject them first.
    for index, amount in enumerate(("10000", "10001", "10002")):
        normal = _process(
            f"%PDF-1.7\nroutine-claim-{index}\n%%EOF".encode(), declared=amount
        )
        assert normal["decision"]["outcome"] == "approved"

    spiked = _process(b"%PDF-1.7\nsudden-large-claim\n%%EOF", declared="100000")

    assert spiked["decision"]["outcome"] == "escalated"
    assert "anomaly_score_high" in spiked["decision"]["reason_codes"]
    assert Decimal(spiked["decision"]["anomaly_score"]) >= Decimal("0.7")


def test_first_claim_has_neutral_anomaly_score() -> None:
    payload = _process(b"%PDF-1.7\nfirst-ever\n%%EOF", declared="50000")

    assert payload["decision"]["outcome"] == "approved"
    assert Decimal(payload["decision"]["anomaly_score"]) == 0

    detail = client.get(f"/claims/{payload['claim']['id']}").json()
    anomaly = next(
        s for s in detail["signals"] if s["signal_type"] == "anomaly"
    )
    assert anomaly["triggered_rules"] == []
    assert anomaly["detector_version"] == "rule-based-v1"


def test_reprocessing_escalated_claim_replays_result() -> None:
    first = _process(b"%PDF-1.7\nescalate-replay\n%%EOF", declared="700000")
    claim_id = first["claim"]["id"]

    second = client.post(f"/claims/{claim_id}/process")

    assert second.status_code == 200
    assert second.json() == first


def _claim() -> "Claim":
    now = datetime.now(UTC)
    return Claim(
        id=uuid4(),
        employee_id="engine-test",
        status=ClaimStatus.PROCESSING,
        submitted_at=now,
        currency="IDR",
        declared_amount=Decimal("60000"),
        created_at=now,
        updated_at=now,
    )


def _duplicate_signal(claim_id) -> Signal:
    return Signal(
        id=uuid4(),
        claim_id=claim_id,
        processing_run_id=uuid4(),
        signal_type=SignalType.DUPLICATE,
        severity=Severity.BLOCKING,
        confidence=Decimal("0.9"),
        match_type=DuplicateMatchType.LIKELY_ATTRIBUTES,
        matched_claim_ids=[uuid4()],
        compared_fields=["vendor", "receipt_date", "total"],
        detector_version="attributes-v1",
        explanation="Same vendor, receipt date, and total as a prior claim.",
        created_at=datetime.now(UTC),
    )


def _blocking_finding(claim_id) -> ValidationFinding:
    return ValidationFinding(
        claim_id=claim_id,
        processing_run_id=uuid4(),
        rule_id="required_total",
        passed=False,
        severity=Severity.BLOCKING,
        reason_code="required_field_missing",
        explanation="Total is missing.",
    )


def _policy_violation(claim_id) -> PolicyEvaluation:
    return PolicyEvaluation(
        claim_id=claim_id,
        processing_run_id=uuid4(),
        policy_id="expense-policy",
        policy_version=1,
        rule_id="meal_daily_limit",
        rule_type="max_amount_per_person",
        passed=False,
        severity=Severity.BLOCKING,
        reason_code="policy_limit_exceeded",
        explanation="Total exceeds the meal limit.",
    )


def test_blocking_finding_takes_precedence_over_duplicate() -> None:
    claim_id = uuid4()

    decision = ENGINE.decide(
        claim=_claim(),
        total=Decimal("60000"),
        confidence=Decimal("0.96"),
        findings=[_blocking_finding(claim_id)],
        evaluations=[],
        signals=[_duplicate_signal(claim_id)],
        policy_version=None,
        processing_run_id=uuid4(),
    )

    assert decision.outcome == "needs_clarification"
    assert decision.reason_codes == ["required_field_missing"]


def test_duplicate_takes_precedence_over_policy_violation() -> None:
    claim_id = uuid4()

    decision = ENGINE.decide(
        claim=_claim(),
        total=Decimal("60000"),
        confidence=Decimal("0.96"),
        findings=[],
        evaluations=[_policy_violation(claim_id)],
        signals=[_duplicate_signal(claim_id)],
        policy_version=1,
        processing_run_id=uuid4(),
    )

    assert decision.outcome == "rejected"
    assert decision.reason_codes == ["duplicate_receipt"]


def _provider_degraded_signal(claim_id) -> "Signal":
    return Signal(
        id=uuid4(),
        claim_id=claim_id,
        processing_run_id=uuid4(),
        signal_type=SignalType.PROVIDER_DEGRADED,
        severity=Severity.WARNING,
        triggered_rules=["provider_fallback"],
        evidence={"provider": "llm-fallback-mock:1"},
        detector_version="provider-fallback-v1",
        explanation="Live extraction provider failed; fallback result in use.",
        created_at=datetime.now(UTC),
    )


def test_provider_degraded_result_is_escalated_not_approved() -> None:
    claim_id = uuid4()

    decision = ENGINE.decide(
        claim=_claim(),
        total=Decimal("60000"),
        confidence=Decimal("0.96"),
        findings=[],
        evaluations=[],
        signals=[_provider_degraded_signal(claim_id)],
        policy_version=1,
        processing_run_id=uuid4(),
    )

    assert decision.outcome == "escalated"
    assert decision.reason_codes[0] == "provider_fallback_active"


def test_same_claim_without_degraded_signal_is_approved() -> None:
    decision = ENGINE.decide(
        claim=_claim(),
        total=Decimal("60000"),
        confidence=Decimal("0.96"),
        findings=[],
        evaluations=[],
        signals=[],
        policy_version=1,
        processing_run_id=uuid4(),
    )

    assert decision.outcome == "approved"


def test_nfr07_decision_determinism_and_property_equivalence() -> None:
    """NFR-07: Konsistensi. Keputusan deterministik: input + policy version sama -> keputusan sama.
    Order-independence: Permutasi urutan evaluasi dan signal tidak mengubah outcome keputusan."""
    import itertools

    claim_id = uuid4()
    run_id = uuid4()
    claim = _claim()

    # Base case: deterministic purity
    args = dict(
        claim=claim,
        total=Decimal("60000"),
        confidence=Decimal("0.95"),
        findings=[],
        evaluations=[_policy_violation(claim_id)],
        signals=[_duplicate_signal(claim_id)],
        policy_version=1,
        processing_run_id=run_id,
    )
    d1 = ENGINE.decide(**args)
    d2 = ENGINE.decide(**args)
    assert d1.outcome == d2.outcome
    assert d1.reason_codes == d2.reason_codes
    assert d1.policy_version == d2.policy_version

    # Property: Order-independence of signals and evaluations
    evals = [_policy_violation(claim_id), PolicyEvaluation(
        claim_id=claim_id, processing_run_id=run_id,
        policy_id="hotel-policy", policy_version=1, rule_id="hotel_limit",
        rule_type="threshold", passed=False, explanation="Exceeds hotel limit",
        severity=Severity.BLOCKING, clarifiable=False, actual_value="800000", limit="600000",
        reason_code="hotel_limit_exceeded"
    )]
    sigs = [_duplicate_signal(claim_id), _provider_degraded_signal(claim_id)]

    outcomes = []
    reason_sets = []
    for perm_evals in itertools.permutations(evals):
        for perm_sigs in itertools.permutations(sigs):
            dec = ENGINE.decide(
                claim=claim,
                total=Decimal("120000"),
                confidence=Decimal("0.90"),
                findings=[],
                evaluations=list(perm_evals),
                signals=list(perm_sigs),
                policy_version=1,
                processing_run_id=uuid4(),
            )
            outcomes.append(dec.outcome)
            reason_sets.append(set(dec.reason_codes))

    assert len(set(outcomes)) == 1, "Decision outcome varied across input permutations!"
    assert all(r == reason_sets[0] for r in reason_sets), "Reason codes varied across input permutations!"
    assert outcomes[0] == "rejected"
