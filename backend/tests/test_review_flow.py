"""M5: clarification conversation, human review, and memory (FR-09/10/15)."""

from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _process(content: bytes, declared: str, employee: str = "m5-test") -> dict:
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


def test_shared_meal_asks_participants_then_approves() -> None:
    # BRD scenario 2: Rp240.000 meal for several people -> ask -> recalculate.
    payload = _process(b"%PDF-1.7\nCATEGORY:MEALS shared-meal\n%%EOF", "240000")
    claim_id = payload["claim"]["id"]

    assert payload["decision"]["outcome"] == "needs_clarification"
    listing = client.get(f"/claims/{claim_id}/clarifications").json()
    assert listing["total"] == 1
    clarification = listing["items"][0]
    assert clarification["code"] == "participant_count_required"
    assert clarification["status"] == "open"

    answer = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "4", "answered_by": "employee-m5"},
    )

    assert answer.status_code == 200, answer.text
    resumed = answer.json()
    assert resumed["claim"]["status"] == "approved"
    assert resumed["decision"]["outcome"] == "approved"
    meal = next(
        e
        for e in resumed["policy_evaluations"]
        if e["rule_id"] == "meal_daily_limit"
    )
    assert meal["passed"] is True
    assert meal["limit"] == "300000"

    # Conversation context preserves the Q&A (FR-15).
    detail = client.get(f"/claims/{claim_id}").json()
    assert len(detail["attempts"]) == 2, "answer must create a NEW run"


def test_answering_twice_is_idempotent() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:MEALS twice-asked\n%%EOF", "240000")
    claim_id = payload["claim"]["id"]
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]

    first = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "2", "answered_by": "employee-m5"},
    )
    assert first.status_code == 200
    attempts_after_first = len(first.json()["attempts"])

    # A repeated submission replays the recorded outcome: no error, no new run.
    second = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "4", "answered_by": "employee-m5"},
    )
    assert second.status_code == 200
    assert second.json()["claim"]["id"] == first.json()["claim"]["id"]
    assert second.json()["decision"] == first.json()["decision"]
    assert len(second.json()["attempts"]) == attempts_after_first

    listing = client.get(f"/claims/{claim_id}/clarifications").json()
    assert listing["total"] == 1, "clarification must not be duplicated"
    assert listing["items"][0]["answer"] == "2", "first answer is preserved"


def test_answered_but_still_over_limit_is_rejected() -> None:
    payload = _process(b"%PDF-1.7\nCATEGORY:MEALS still-over\n%%EOF", "400000")
    claim_id = payload["claim"]["id"]
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]

    answer = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "1", "answered_by": "employee-m5"},
    )

    assert answer.status_code == 200
    assert answer.json()["decision"]["outcome"] == "rejected"


def test_escalated_claim_flows_through_review_queue() -> None:
    payload = _process(b"%PDF-1.7\nescalate-me\n%%EOF", "700000")
    claim_id = payload["claim"]["id"]
    assert payload["decision"]["outcome"] == "escalated"

    queue = client.get("/reviews").json()
    assert queue["total"] == 1
    assert queue["items"][0]["claim"]["id"] == claim_id
    assert queue["items"][0]["decision"]["reason_codes"]

    decision = client.post(
        f"/reviews/{claim_id}/decision",
        json={
            "action": "approve",
            "reason": "Trip to supplier verified with manager.",
            "reviewer_reference": "reviewer-01",
        },
    )

    assert decision.status_code == 200, decision.text
    body = decision.json()
    assert body["decision"]["outcome"] == "approved"
    assert body["decision"]["created_by"] == "reviewer"
    assert body["claim"]["status"] == "approved"
    assert body["review"]["status"] == "decided"

    # Reviewer action is attributable and the queue is now empty.
    assert client.get("/reviews").json()["total"] == 0

    detail = client.get(f"/claims/{claim_id}").json()
    outcomes = [d["outcome"] for d in detail["decisions"]]
    assert outcomes == ["escalated", "approved"], "agent decision is preserved"


def test_second_review_decision_is_rejected() -> None:
    payload = _process(b"%PDF-1.7\nescalate-once\n%%EOF", "700000")
    claim_id = payload["claim"]["id"]
    client.post(
        f"/reviews/{claim_id}/decision",
        json={"action": "reject", "reason": "No receipt evidence.", "reviewer_reference": "reviewer-01"},
    )

    again = client.post(
        f"/reviews/{claim_id}/decision",
        json={"action": "approve", "reason": "Changed my mind.", "reviewer_reference": "reviewer-02"},
    )

    assert again.status_code == 409


def test_review_decision_requires_reason() -> None:
    payload = _process(b"%PDF-1.7\nescalate-reason\n%%EOF", "700000")
    claim_id = payload["claim"]["id"]

    response = client.post(
        f"/reviews/{claim_id}/decision",
        json={"action": "approve", "reason": "", "reviewer_reference": "reviewer-01"},
    )

    assert response.status_code == 422


def test_answered_confidence_clarification_escalates_to_review_without_loop() -> None:
    payload = _process(b"%PDF-1.7\nLOW_CONFIDENCE unreadable\n%%EOF", "60000")
    claim_id = payload["claim"]["id"]
    assert payload["claim"]["status"] == "needs_clarification"

    listing = client.get(f"/claims/{claim_id}/clarifications").json()
    assert listing["total"] == 1
    clarification = listing["items"][0]

    answer = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "Kopi Kenangan, 10 Nov 2026", "answered_by": "employee-m5"},
    )
    assert answer.status_code == 200, answer.text
    resumed = answer.json()
    assert resumed["claim"]["status"] == "escalated"
    assert resumed["decision"]["outcome"] == "escalated"

    reviews = client.get("/reviews").json()
    assert any(item["claim"]["id"] == claim_id for item in reviews["items"])

