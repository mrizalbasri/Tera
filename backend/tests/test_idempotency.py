"""Regression tests for the PR #7 review priorities.

Covers: claim idempotency (sequential and concurrent), processing
idempotency keys, retry semantics, timeline completeness/isolation, audit
sequence atomicity, payload safety, and explicit persistence failures.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.config import Settings, get_settings
from app.main import app
from app.audit.events import record_audit_event
from app.domain.enums import ActorType
from app.repositories.memory import (
    InMemoryAuditRepository,
    InMemoryClaimRepository,
)
from app.repositories.sql import SqlRepositories

client = TestClient(app)


def _create(content: bytes, declared: str, employee: str, key: str | None = None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/claims",
        data={"employee_id": employee, "declared_amount": declared},
        files={"files": ("receipt.pdf", __import__("io").BytesIO(content), "application/pdf")},
        headers=headers,
    )


def _process(claim_id: str, key: str | None = None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(f"/claims/{claim_id}/process", headers=headers)


# --- Priority 1: claim idempotency -------------------------------------------


def test_same_idempotency_key_returns_same_claim_without_duplicates() -> None:
    first = _create(b"%PDF-1.7\nidem-A\n%%EOF", "60000", "idem-user", key="k-claim-1")
    second = _create(b"%PDF-1.7\nidem-B\n%%EOF", "60000", "idem-user", key="k-claim-1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["idempotent_replay"] is True
    assert second.json()["claim"]["id"] == first.json()["claim"]["id"]

    listing = client.get("/claims", params={"employee_id": "idem-user"}).json()
    assert listing["total"] == 1, "no duplicate claim may exist"
    assert len(listing["items"][0]) > 0


def test_reserve_idempotency_key_is_atomic_across_threads() -> None:
    repo = InMemoryClaimRepository()
    key = "race-key"
    barrier = Barrier(16)

    def reserve() -> bool:
        barrier.wait()
        return repo.reserve_idempotency_key(key, uuid4())

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: reserve(), range(16)))

    assert sum(1 for won in results if won) == 1, "exactly one reservation wins"


def test_concurrent_same_key_requests_create_one_claim() -> None:
    barrier = Barrier(4)

    def submit(index: int):
        barrier.wait()
        return _create(
            f"%PDF-1.7\nconcurrent-{index}\n%%EOF".encode(),
            "60000",
            "concurrent-user",
            key="k-concurrent",
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(submit, range(4)))

    assert all(response.status_code == 201 for response in responses)
    claim_ids = {response.json()["claim"]["id"] for response in responses}
    assert len(claim_ids) == 1, "all concurrent duplicates resolve to one claim"

    listing = client.get("/claims", params={"employee_id": "concurrent-user"}).json()
    assert listing["total"] == 1


def test_sql_reserve_conflicts_are_rejected(tmp_path) -> None:
    from app.domain.enums import ClaimStatus
    from app.schemas.core import Claim

    repos = SqlRepositories(f"sqlite:///{tmp_path / 'idem.db'}")
    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
    claim = repos.claims.save(
        Claim(
            id=uuid4(),
            employee_id="sql-idem",
            status=ClaimStatus.RECEIVED,
            submitted_at=now,
            currency="IDR",
            declared_amount=None,
            created_at=now,
            updated_at=now,
        )
    )

    assert repos.claims.reserve_idempotency_key("sql-key", claim.id) is True
    assert repos.claims.reserve_idempotency_key("sql-key", uuid4()) is False
    assert repos.claims.get_by_idempotency_key("sql-key").id == claim.id


# --- Priority 2: processing idempotency ---------------------------------------


def test_same_processing_key_replays_run_without_new_run() -> None:
    created = _create(b"%PDF-1.7\nproc-key\n%%EOF", "60000", "proc-user")
    claim_id = created.json()["claim"]["id"]

    first = _process(claim_id, key="k-run-1")
    second = _process(claim_id, key="k-run-1")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    run_ids = {
        attempt["processing_run_id"]
        for attempt in second.json()["attempts"]
    }
    assert len(run_ids) == 1, "no second ProcessingRun may be created"


def test_different_processing_key_after_failure_creates_new_run() -> None:
    created = _create(
        b"%PDF-1.7\nMALFORMED proc-retry\n%%EOF", "60000", "retry-user"
    )
    claim_id = created.json()["claim"]["id"]

    first = _process(claim_id, key="k-attempt-1")
    assert first.status_code == 502

    second = _process(claim_id, key="k-attempt-2")
    assert second.status_code == 502, "retry against MALFORMED fixture fails again"

    # Same key replays the same failed run; a new key really creates a new run.
    same_again = _process(claim_id, key="k-attempt-2")
    assert same_again.status_code == 502
    third = _process(claim_id, key="k-attempt-3")
    assert third.status_code == 502

    detail = client.get(f"/claims/{claim_id}").json()
    run_ids = {attempt["processing_run_id"] for attempt in detail["attempts"]}
    assert len(run_ids) == 3, "each distinct key created exactly one new run"
    assert len(detail["attempts"]) == 3, "previous run history is preserved"


def test_previous_runs_and_decisions_survive_keyed_replays() -> None:
    created = _create(
        b"%PDF-1.7\nCATEGORY:MEALS keyed-clarify\n%%EOF", "240000", "history-user"
    )
    claim_id = created.json()["claim"]["id"]
    first = _process(claim_id, key="k-hist-1")
    assert first.json()["decision"]["outcome"] == "needs_clarification"
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]
    answered = client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "4", "answered_by": "history-user"},
    )
    assert answered.json()["decision"]["outcome"] == "approved"

    _process(claim_id, key="k-hist-1")  # keyed replay must not add runs

    detail = client.get(f"/claims/{claim_id}").json()
    assert len(detail["attempts"]) == 2
    assert [d["outcome"] for d in detail["decisions"]] == [
        "needs_clarification",
        "approved",
    ], "earlier runs and decisions are never erased"


# --- Priority 3: timeline completeness and ordering ---------------------------


def test_timeline_covers_the_full_lifecycle() -> None:
    created = _create(
        b"%PDF-1.7\nCATEGORY:MEALS timeline-full\n%%EOF", "240000", "tl-user"
    )
    claim_id = created.json()["claim"]["id"]
    _process(claim_id)
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][0]
    client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": "2", "answered_by": "tl-user"},
    )

    payload = client.get(f"/claims/{claim_id}/timeline").json()
    items = payload["items"]
    names = [entry["step_name"] for entry in items]

    assert names[0] == "claim.received"
    expected = {
        "run.started",
        "extraction_attempt",
        "extraction",
        "validation",
        "policy",
        "signal.anomaly",
        "decision",
        "clarification",
        "clarification.answered",
        "run.completed",
        "audit.claim.received",
        "audit.processing_run.completed",
        "audit.clarification.answered",
    }
    assert expected <= set(names), f"missing steps: {expected - set(names)}"
    assert [entry["sequence"] for entry in items] == list(range(1, len(items) + 1))

    for entry in items:
        assert set(entry) >= {
            "sequence",
            "step_name",
            "status",
            "timestamp",
            "processing_run_id",
            "summary",
            "error_code",
            "detail",
        }
    validation_failures = [
        e for e in items if e["step_name"] == "policy" and e["status"] == "failed"
    ]
    assert validation_failures, "the first run's failed per-person limit is visible"
    assert any(
        failure["detail"]["rule_id"] == "meal_daily_limit"
        for failure in validation_failures
    )


def test_timeline_is_scoped_to_one_claim() -> None:
    # Distinct amounts so duplicate detection does not legitimately reference
    # the other claim in its evidence.
    other = _create(b"%PDF-1.7\nother-claim\n%%EOF", "61000", "isolation-other")
    _process(other.json()["claim"]["id"])

    mine = _create(b"%PDF-1.7\nmy-claim\n%%EOF", "60000", "isolation-mine")
    my_id = mine.json()["claim"]["id"]
    _process(my_id)

    payload = client.get(f"/claims/{my_id}/timeline").text

    assert other.json()["claim"]["id"] not in payload
    assert "isolation-other" not in payload


# --- Priority 4: audit sequence and safety -------------------------------------


def test_concurrent_audit_appends_get_unique_sequences() -> None:
    aggregate = uuid4()
    repo = InMemoryAuditRepository()
    barrier = Barrier(12)

    def append(_: int):
        from app.audit.events import record_audit_event
        from app.domain.enums import ActorType

        barrier.wait()
        return record_audit_event(
            repo,
            aggregate_type="claim",
            aggregate_id=aggregate,
            event_type=f"event-{_}",
            actor_type=ActorType.AGENT,
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        events = list(pool.map(append, range(12)))

    sequences = sorted(event.sequence_number for event in events)
    assert sequences == list(range(1, 13)), "no duplicates, no gaps"


def test_sql_concurrent_audit_appends_get_unique_sequences(tmp_path) -> None:
    repos = SqlRepositories(f"sqlite:///{tmp_path / 'audit.db'}")
    aggregate = uuid4()
    barrier = Barrier(8)

    def append(_: int):
        from app.audit.events import record_audit_event
        from app.domain.enums import ActorType

        barrier.wait()
        return record_audit_event(
            repos.audit,
            aggregate_type="claim",
            aggregate_id=aggregate,
            event_type=f"event-{_}",
            actor_type=ActorType.AGENT,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        events = list(pool.map(append, range(8)))

    sequences = sorted(event.sequence_number for event in events)
    assert sequences == list(range(1, 9)), "atomic sequence allocation per aggregate"


def test_audit_events_never_contain_receipt_bytes() -> None:
    created = _create(b"%PDF-1.7\naudit-leak-check\n%%EOF", "60000", "audit-user")
    claim_id = created.json()["claim"]["id"]
    _process(claim_id)

    repos = deps._memory_repositories()
    events = repos.audit.list_for_aggregate("claim", UUID(claim_id))
    raw = json.dumps([event.model_dump(mode="json") for event in events])

    assert events, "expected audit events for the claim"
    assert "%PDF" not in raw
    assert "audit-leak-check" not in raw


# --- Priority 5: explicit persistence failures ----------------------------------


def test_persistence_failure_is_explicit(tmp_path) -> None:
    bad_url = f"sqlite:///{tmp_path / 'missing-dir' / 'x.db'}"

    with pytest.raises(Exception) as excinfo:
        SqlRepositories(bad_url)

    assert "unable to open database file" in str(excinfo.value).lower()


def test_sql_keyed_processing_survives_restart(tmp_path) -> None:
    db_path = tmp_path / "keyed.db"
    settings = Settings(
        _env_file=None,
        storage_backend="sql",
        database_url=f"sqlite:///{db_path}",
    )
    deps._sql_repositories.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        created = client.post(
            "/claims",
            data={"employee_id": "sql-key-user", "declared_amount": "60000"},
            files={
                "files": (
                    "receipt.pdf",
                    __import__("io").BytesIO(b"%PDF-1.7\nsql-keyed\n%%EOF"),
                    "application/pdf",
                )
            },
        )
        claim_id = created.json()["claim"]["id"]
        first = _process(claim_id, key="k-sql-1")
        assert first.status_code == 200

        deps._sql_repositories.cache_clear()  # simulated restart
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            storage_backend="sql",
            database_url=f"sqlite:///{db_path}",
        )
        replay = _process(claim_id, key="k-sql-1")

        assert replay.status_code == 200
        assert replay.json() == first.json()
    finally:
        app.dependency_overrides.pop(get_settings)
        deps._sql_repositories.cache_clear()


def test_audit_is_isolated_across_aggregate_types_with_same_id() -> None:
    """A claim and a receipt sharing one id must never share audit sequences."""
    shared_id = uuid4()

    repo = InMemoryAuditRepository()
    record_audit_event(
        repo,
        aggregate_type="claim",
        aggregate_id=shared_id,
        event_type="claim.received",
        actor_type=ActorType.EMPLOYEE,
    )
    record_audit_event(
        repo,
        aggregate_type="claim",
        aggregate_id=shared_id,
        event_type="claim.updated",
        actor_type=ActorType.AGENT,
    )
    record_audit_event(
        repo,
        aggregate_type="receipt",
        aggregate_id=shared_id,
        event_type="receipt.stored",
        actor_type=ActorType.AGENT,
    )

    claims = repo.list_for_aggregate("claim", shared_id)
    receipts = repo.list_for_aggregate("receipt", shared_id)

    assert [event.sequence_number for event in claims] == [1, 2]
    assert [event.sequence_number for event in receipts] == [1]
    assert all(event.aggregate_type == "claim" for event in claims)
    assert all(event.aggregate_type == "receipt" for event in receipts)


def test_sql_audit_is_isolated_across_aggregate_types_with_same_id(tmp_path) -> None:
    repos = SqlRepositories(f"sqlite:///{tmp_path / 'isolation.db'}")
    shared_id = uuid4()

    record_audit_event(
        repos.audit,
        aggregate_type="claim",
        aggregate_id=shared_id,
        event_type="claim.received",
        actor_type=ActorType.EMPLOYEE,
    )
    record_audit_event(
        repos.audit,
        aggregate_type="claim",
        aggregate_id=shared_id,
        event_type="claim.updated",
        actor_type=ActorType.AGENT,
    )
    record_audit_event(
        repos.audit,
        aggregate_type="receipt",
        aggregate_id=shared_id,
        event_type="receipt.stored",
        actor_type=ActorType.AGENT,
    )

    claims = repos.audit.list_for_aggregate("claim", shared_id)
    receipts = repos.audit.list_for_aggregate("receipt", shared_id)

    assert [event.sequence_number for event in claims] == [1, 2]
    assert [event.sequence_number for event in receipts] == [1]
    assert len(claims) == 2 and len(receipts) == 1
