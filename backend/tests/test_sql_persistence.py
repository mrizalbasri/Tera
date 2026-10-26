"""M6 contract tests: the SQL storage backend is a drop-in for memory.

The same user journeys run against ``storage_backend=sql`` (SQLite), data
survives a simulated restart (repository cache cleared, same database file),
and the timeline renders an ordered trace.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def sql_env(tmp_path):
    """Point the app at a fresh SQLite file and return (client, db_path)."""
    db_path = tmp_path / "m6-contract.db"
    settings = Settings(
        _env_file=None,
        storage_backend="sql",
        database_url=f"sqlite:///{db_path}",
    )
    deps._sql_repositories.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app), db_path
    app.dependency_overrides.pop(get_settings)
    deps._sql_repositories.cache_clear()


def _create(client: TestClient, content: bytes, declared: str, employee: str) -> str:
    response = client.post(
        "/claims",
        data={"employee_id": employee, "declared_amount": declared},
        files={"files": ("receipt.pdf", __import__("io").BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["claim"]["id"]


def test_sql_backend_runs_the_full_pipeline(sql_env) -> None:
    client, _ = sql_env

    created = client.post(
        "/claims",
        data={"employee_id": "sql-user", "declared_amount": "60000"},
        files={
            "files": (
                "receipt.pdf",
                __import__("io").BytesIO(b"%PDF-1.7\nCATEGORY:MEALS sql-flow\n%%EOF"),
                "application/pdf",
            )
        },
    )
    assert created.status_code == 201, created.text
    claim_id = created.json()["claim"]["id"]

    processed = client.post(f"/claims/{claim_id}/process")

    assert processed.status_code == 200, processed.text
    assert processed.json()["decision"]["outcome"] == "approved"
    assert processed.json()["decision"]["policy_version"] == 1


def test_sql_backend_persists_across_restart(sql_env) -> None:
    client, db_path = sql_env
    claim_id = _create(
        client, b"%PDF-1.7\npersist-me\n%%EOF", "60000", "sql-persist"
    )
    client.post(f"/claims/{claim_id}/process")

    # Simulate a restart: drop the cached engine/session, same database file.
    deps._sql_repositories.cache_clear()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        storage_backend="sql",
        database_url=f"sqlite:///{db_path}",
    )

    detail = client.get(f"/claims/{claim_id}")

    assert detail.status_code == 200
    assert detail.json()["claim"]["status"] == "approved"
    assert len(detail.json()["decisions"]) == 1
    assert detail.json()["receipts"][0]["content_hash"]

    # Reprocessing an approved claim replays the recorded run.
    replay = client.post(f"/claims/{claim_id}/process")
    assert replay.status_code == 200
    assert replay.json()["decision"]["outcome"] == "approved"


def test_sql_backend_supports_clarification_and_review(sql_env) -> None:
    client, _ = sql_env

    # Shared meal -> clarification -> answer -> approved on SQL storage.
    meal_id = _create(
        client, b"%PDF-1.7\nCATEGORY:MEALS sql-shared\n%%EOF", "240000", "sql-clarity"
    )
    client.post(f"/claims/{meal_id}/process")
    clarification = client.get(f"/claims/{meal_id}/clarifications").json()["items"][0]
    answered = client.post(
        f"/claims/{meal_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "4", "answered_by": "sql-user"},
    )
    assert answered.status_code == 200
    assert answered.json()["decision"]["outcome"] == "approved"

    # Over-threshold claim -> escalation -> reviewer approves, still on SQL.
    escalated_id = _create(
        client, b"%PDF-1.7\nsql-escalate\n%%EOF", "700000", "sql-review"
    )
    client.post(f"/claims/{escalated_id}/process")
    queue = client.get("/reviews").json()
    assert queue["total"] == 1
    reviewed = client.post(
        f"/reviews/{escalated_id}/decision",
        json={
            "action": "approve",
            "reason": "Verified against trip records.",
            "reviewer_reference": "reviewer-sql",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["claim"]["status"] == "approved"


def test_sql_backend_rejects_duplicate_like_memory(sql_env) -> None:
    client, _ = sql_env
    first_id = _create(client, b"%PDF-1.7\nsql-dup-A\n%%EOF", "30000", "sql-dup-1")
    client.post(f"/claims/{first_id}/process")

    second_id = _create(
        client, b"%PDF-1.7\nsql-dup-B\n%%EOF", "30000", "sql-dup-2"
    )
    payload = client.post(f"/claims/{second_id}/process").json()

    assert payload["decision"]["outcome"] == "rejected"
    assert payload["decision"]["reason_codes"] == ["duplicate_receipt"]


def test_timeline_is_ordered_and_explains_the_outcome() -> None:
    client = TestClient(app)
    claim_id = _create(
        client, b"%PDF-1.7\nCATEGORY:MEALS timeline-me\n%%EOF", "240000", "timeline-user"
    )
    client.post(f"/claims/{claim_id}/process")
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]
    client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "4", "answered_by": "timeline-user"},
    )

    timeline = client.get(f"/claims/{claim_id}/timeline")

    assert timeline.status_code == 200
    items = timeline.json()["items"]
    assert [entry["sequence"] for entry in items] == list(range(1, len(items) + 1))
    names = [entry["step_name"] for entry in items]
    assert names[0] == "claim.received"
    assert "run.started" in names and "run.completed" in names
    assert "decision" in names and "clarification" in names
    assert "clarification.answered" in names
    decisions = [entry for entry in items if entry["step_name"] == "decision"]
    assert [d["status"] for d in decisions] == ["needs_clarification", "approved"]
    assert decisions[-1]["status"] == "approved"
    # Raw receipt bytes never leak; content hashes appear as 12-char prefixes only.
    raw = timeline.text
    assert "%PDF" not in raw
    hashes = [
        receipt["content_hash"]
        for entry in items
        if entry["step_name"] == "claim.received"
        for receipt in entry["detail"]["receipts"]
    ]
    assert hashes and all(len(h) == 12 for h in hashes)
