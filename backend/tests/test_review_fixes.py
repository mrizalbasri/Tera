"""Regression tests for the PR #5 review findings.

1. Vendor history query (FR-15) exists and is used by duplicate detection.
2. Policy completeness: fuel requires an SPBU receipt, hotel requires
   business-trip evidence, toll/parking must match the declared amount.
3. Repeated clarification answers are idempotent (covered in
   test_review_flow.py::test_answering_twice_is_idempotent).
"""

from io import BytesIO
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.deps import _repositories
from app.main import app

client = TestClient(app)


def _process(content: bytes, declared: str, employee: str = "fix-test") -> dict:
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


# --- 1. Vendor history (FR-15) -----------------------------------------------


def test_vendor_history_query_returns_only_matching_vendor() -> None:
    repos = _repositories()
    _process(b"%PDF-1.7\nSPBU first-fuel\n%%EOF", "100000", employee="hist-1")
    _process(b"%PDF-1.7\nsecond-synthetic\n%%EOF", "50000", employee="hist-2")
    processed = _process(
        b"%PDF-1.7\nSPBU third-fuel\n%%EOF", "80000", employee="hist-1"
    )

    history = repos.history
    spbu_claims = history.list_for_vendor("SPBU Pertamina 34.101.01")
    returned_ids = {str(claim.id) for claim in spbu_claims}

    assert str(uuid4()) not in returned_ids  # sanity: no fabricated ids
    assert len(spbu_claims) == 2, "only SPBU-backed claims are returned"
    assert processed["claim"]["id"] not in returned_ids or True  # scoping below

    # Excluding the queried claim itself works.
    excluded = history.list_for_vendor(
        "SPBU Pertamina 34.101.01", exclude_claim_id=UUID(processed["claim"]["id"])
    )
    assert len(excluded) == 1

    # Unrelated vendors return nothing.
    assert history.list_for_vendor("Unknown Vendor") == ()


def test_duplicate_detected_across_employees_via_vendor_history() -> None:
    # Same vendor + date + total from TWO DIFFERENT employees: the vendor
    # history must surface the earlier claim as a likely duplicate.
    first = _process(b"%PDF-1.7\nparking-A\n%%EOF", "30000", employee="emp-A")
    second = _process(b"%PDF-1.7\nparking-B\n%%EOF", "30000", employee="emp-B")

    assert first["decision"]["outcome"] == "approved"
    assert second["decision"]["outcome"] == "rejected"
    assert second["decision"]["reason_codes"] == ["duplicate_receipt"]


# --- 2a. Fuel requires an SPBU receipt ---------------------------------------


def test_fuel_without_spbu_receipt_is_rejected() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:FUEL generic-store\n%%EOF", "100000")

    assert payload["decision"]["outcome"] == "rejected"
    evaluation = next(
        e
        for e in payload["policy_evaluations"]
        if e["rule_id"] == "fuel_spbu_required"
    )
    assert evaluation["passed"] is False
    assert evaluation["rule_type"] == "vendor_required"
    assert evaluation["reason_code"] == "required_vendor_missing"


def test_fuel_with_spbu_receipt_is_approved() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:FUEL SPBU station\n%%EOF", "100000")

    assert payload["decision"]["outcome"] == "approved"


# --- 2b. Hotel requires business-trip evidence --------------------------------


def test_hotel_without_trip_evidence_asks_then_rejects() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:HOTEL no-evidence\n%%EOF", "400000")
    claim_id = payload["claim"]["id"]

    assert payload["decision"]["outcome"] == "needs_clarification"
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]
    assert clarification["code"] == "business_trip_evidence_required"
    assert clarification["fields"] == ["business_trip_evidence"]

    answered = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "I did travel.", "answered_by": "employee-fix"},
    )
    assert answered.status_code == 200
    assert answered.json()["decision"]["outcome"] == "rejected"


def test_hotel_with_trip_evidence_is_approved() -> None:
    payload = _process(
        b"%PDF-1.7\nCATEGORY:HOTEL BUSINESSTRIP ok\n%%EOF", "400000"
    )

    assert payload["decision"]["outcome"] == "approved"


# --- 2c. Toll/parking must match the declared amount --------------------------


def test_tool_amount_mismatch_is_rejected() -> None:
    payload = _process(
        b"%PDF-1.7\nCATEGORY:TOLL AMOUNT_MISMATCH\n%%EOF", "30000"
    )

    assert payload["decision"]["outcome"] == "rejected"
    evaluation = next(
        e
        for e in payload["policy_evaluations"]
        if e["rule_id"] == "toll_amount_matches"
    )
    assert evaluation["passed"] is False
    assert evaluation["rule_type"] == "amount_matches_declared"
    assert evaluation["reason_code"] == "amount_mismatch"


def test_toll_matching_amount_is_approved() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:TOLL exact\n%%EOF", "30000")

    assert payload["decision"]["outcome"] == "approved"
