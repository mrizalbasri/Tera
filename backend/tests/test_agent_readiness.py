from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent.runtime import graph_resources
from app.api import deps
from app.api.claim_access import ClaimActor, get_claim_actor
from app.config import Settings, get_settings
from app.errors import ApplicationError
from app.evaluate_agent import evaluate
from app.integrations.llm import LlmExtractionOutput
from app.main import app
from app.repositories.memory import InMemoryRepositories
from app.repositories.migrations import CURRENT_VERSION, schema_version, upgrade
from app.repositories.sql import SqlRepositories
from app.schemas.core import Claim, ProcessingRun
from app.services.notifications import NotificationService
from app.services.policy_versions import PolicyDraft, PolicyVersionService
from app.services.time_metrics import claim_time_metrics


@pytest.fixture(params=["memory", "sqlite", "postgres"])
def bundle(request, tmp_path):
    if request.param == "memory":
        backend = InMemoryRepositories()
        settings = Settings(_env_file=None, storage_backend="memory", clerk_admin_user_ids="finance")
    else:
        url = request.getfixturevalue("postgres_database_url") if request.param == "postgres" else f"sqlite:///{tmp_path}/ops.db"
        backend = SqlRepositories(url)
        settings = Settings(_env_file=None, storage_backend="sql", database_url=url,
                            graph_checkpoint_path=str(tmp_path / "graph.db"), clerk_admin_user_ids="finance")
    resources = graph_resources(backend, settings)
    yield backend, settings, resources
    resources.close()
    if hasattr(backend, "close"):
        backend.close()


def draft(start=date(2026, 1, 1), end=date(2026, 12, 31)):
    return PolicyDraft(category="meals", effective_from=start, effective_to=end, source="Synthetic company policy",
        rules=[{"rule_id": "meal_limit", "rule_type": "max_amount_per_person", "limit": "50000"}])


def test_policy_publish_is_immutable_conflict_checked_and_date_selected(bundle):
    backend, _, resources = bundle
    service = PolicyVersionService(backend, resources)
    created = service.create(draft(), "finance")
    id = UUID(created["id"])
    edited = service.edit(id, draft(), 1, "finance")
    with pytest.raises(ApplicationError, match="Data sudah berubah"):
        service.edit(id, draft(), 1, "finance")
    published = service.publish(id, edited["revision"], "finance")
    assert published["payload"]["published_by"] == "finance"
    assert len(published["payload"]["fingerprint"]) == 64
    assert service.effective("meals", date(2026, 7, 1)).version == 2
    assert service.effective("meals", date(2025, 12, 31)) is None
    with pytest.raises(ApplicationError) as immutable:
        service.edit(id, draft(), published["revision"], "finance")
    assert immutable.value.code == "policy_immutable"
    overlapping = service.create(draft(), "finance")
    with pytest.raises(ApplicationError) as overlap:
        service.publish(UUID(overlapping["id"]), 1, "finance")
    assert overlap.value.code == "policy_dates_overlap"
    next_version = service.create(draft(date(2027, 2, 1), date(2027, 12, 31)), "finance")
    assert service.publish(UUID(next_version["id"]), 1, "finance")["payload"]["policy"]["version"] == 3
    with pytest.raises(ApplicationError) as gap:
        service.effective("meals", date(2027, 1, 1))
    assert gap.value.code == "policy_date_gap"


def test_concurrent_publications_only_publish_once(bundle):
    backend, _, resources = bundle
    service = PolicyVersionService(backend, resources)
    created = service.create(draft(), "finance")

    def publish():
        try:
            return service.publish(UUID(created["id"]), 1, "finance")["payload"]["status"]
        except ApplicationError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: publish(), range(2)))
    assert sorted(results) == ["published", "record_changed"]


def test_baseline_import_is_idempotent_and_open_ended_policy_can_be_superseded(bundle):
    backend, _, resources = bundle
    service = PolicyVersionService(backend, resources)
    initial = service.seed_baseline("finance")
    assert len(initial) == 5
    assert [r["id"] for r in service.seed_baseline("finance")] == [r["id"] for r in initial]
    record = service.create(draft(date(2026, 10, 1), None), "finance")
    published = service.publish(UUID(record["id"]), 1, "finance")
    assert service.effective("meals", date(2026, 9, 30)).version == 1
    assert service.effective("meals", date(2026, 10, 1)).version == 2
    assert service.effective("meals", date(2027, 1, 1)).version == 2
    assert len(backend.audit.list_for_aggregate("policy_version", UUID(published["id"]))) == 2
    assert initial[0]["payload"]["policy"]["version"] == 1


def test_policy_terms_are_normalized_before_publication():
    policy = PolicyDraft(category="meals", effective_from=date.today(), source="Synthetic",
                         rules=[{"rule_id": "prohibited", "rule_type": "prohibited_items", "prohibited_terms": [" ALCOHOL "]},
                                {"rule_id": "vendor", "rule_type": "vendor_required", "required_terms": [" SPBU "]}])
    assert policy.rules[0].prohibited_terms == ["alcohol"]
    assert policy.rules[1].required_terms == ["spbu"]


def test_import_after_custom_policy_cannot_override_stricter_rules(bundle):
    backend, _, resources = bundle
    service = PolicyVersionService(backend, resources)
    custom = draft(date(2026, 1, 1), None)
    custom.rules[0].limit = Decimal("30000")
    record = service.create(custom, "finance")
    service.publish(UUID(record["id"]), 1, "finance")
    service.seed_baseline("finance")
    effective = service.effective("meals", date(2026, 10, 22))
    assert effective.version == 2
    assert effective.rules[0].limit == Decimal("30000")


def test_policy_date_gap_reaches_review_queue_instead_of_failed_run():
    from io import BytesIO

    client = TestClient(app)
    today = date.today()
    old = draft(today - timedelta(days=10), today - timedelta(days=5)).model_dump(mode="json")
    record = client.post("/policies", json=old).json()
    assert client.post(f"/policies/{record['id']}/publish", json={"revision": 1}).status_code == 200
    created = client.post("/claims", data={"employee_id": "synthetic-date-gap", "declared_amount": "60000"},
                          files={"files": ("synthetic.pdf", BytesIO(b"%PDF-1.7\nCATEGORY:MEALS gap\n%%EOF"), "application/pdf")}).json()
    claim_id = created["claim"]["id"]
    response = client.post(f"/claims/{claim_id}/process")
    assert response.status_code == 200, response.text
    assert response.json()["claim"]["status"] == "escalated"
    assert "policy_date_gap" in response.json()["decision"]["reason_codes"]
    assert response.json()["decision"]["policy_version"] is None
    assert any(row["claim"]["id"] == claim_id for row in client.get("/reviews").json()["items"])


@pytest.mark.parametrize("rules", [
    [{"rule_id": "x", "rule_type": "execute_python"}],
    [{"rule_id": "x", "rule_type": "max_amount", "limit": -1}],
    [{"rule_id": "x", "rule_type": "vendor_required", "required_terms": [""]}],
])
def test_policy_rejects_unsupported_rules(rules):
    with pytest.raises(ValidationError):
        PolicyDraft(category="meals", effective_from=date.today(), source="Synthetic", rules=rules)


def test_notifications_replay_reminder_ownership_and_resolution(bundle):
    backend, settings, _ = bundle
    now = datetime.now(UTC)
    claim = Claim(id=uuid4(), employee_id="employee-a", status="needs_clarification", currency="IDR",
                  submitted_at=now, created_at=now, updated_at=now)
    backend.claims.save(claim)
    service = NotificationService(backend, settings)
    service.sync_claim(claim.id, now=now)
    service.sync_claim(claim.id, now=now)
    assert len(service.inbox("employee-a")) == 1
    assert service.inbox("employee-b") == []
    notification = service.inbox("employee-a")[0]
    with pytest.raises(ApplicationError) as foreign:
        service.mark_read("employee-b", UUID(notification["id"]))
    assert foreign.value.status_code == 404
    marked = service.mark_read("employee-a", UUID(notification["id"]))
    assert service.mark_read("employee-a", UUID(notification["id"]))["revision"] == marked["revision"]
    tomorrow = now + timedelta(hours=25)
    service.sync_claim(claim.id, now=tomorrow)
    service.sync_claim(claim.id, now=tomorrow)
    assert len(service.inbox("employee-a")) == 2
    backend.claims.save(claim.model_copy(update={"status": "approved", "current_decision_id": uuid4(), "updated_at": tomorrow}))
    service.sync_claim(claim.id, now=tomorrow)
    items = service.inbox("employee-a")
    assert sum(not row["payload"]["resolved"] for row in items) == 1
    assert next(row for row in items if not row["payload"]["resolved"])["payload"]["status"] == "approved"


def test_operational_records_survive_restart_and_migration_is_repeatable(tmp_path):
    url = f"sqlite:///{tmp_path}/restart.db"
    first = SqlRepositories(url)
    record = {"id": str(uuid4()), "namespace": "notifications", "owner": "a", "aggregate_id": str(uuid4()),
              "created_at": datetime.now(UTC).isoformat(), "revision": 1, "payload": {"read_at": None}}
    first.operational.insert(record)
    upgrade(first._engine)
    with first._engine.connect() as connection:
        assert schema_version(connection) == CURRENT_VERSION
    first.close()
    second = SqlRepositories(url, initialize_schema=False)
    assert second.operational.get(record["id"]) == record
    second.close()


@pytest.mark.parametrize("printed,expected", [("16.000", "16000"), ("Rp50.000", "50000"), ("16.000,50", "16000.50"), (16, "16")])
def test_live_contract_normalizes_printed_money_without_multiplying_numeric(printed, expected):
    result = LlmExtractionOutput(vendor="Synthetic", receipt_date="2026-10-22", total=printed,
                                 currency="IDR", category="meals", confidence="0.96")
    assert result.total == Decimal(expected)


def test_time_metrics_merge_overlaps_and_exclude_human_wait_from_active():
    start = datetime(2026, 10, 23, tzinfo=UTC)
    claim_id = uuid4()
    runs = [ProcessingRun(id=uuid4(), claim_id=claim_id, status="needs_clarification", pipeline_version="test",
                          started_at=start, completed_at=start + timedelta(seconds=10)),
            ProcessingRun(id=uuid4(), claim_id=claim_id, status="succeeded", pipeline_version="test",
                          started_at=start + timedelta(seconds=70), completed_at=start + timedelta(seconds=80))]
    assert claim_time_metrics(runs, now=start + timedelta(seconds=100)) == {
        "active_ms": 20000, "employee_wait_ms": 60000, "reviewer_wait_ms": 0}
    assert claim_time_metrics([], now=start)["active_ms"] is None


def test_future_date_still_blocks_after_json_persistence_roundtrip():
    from app.integrations.mock import MockReceiptExtractor
    from app.schemas.core import ExtractionResult, Receipt
    from app.services.validation import ValidationService

    now = datetime.now(UTC)
    claim = Claim(id=uuid4(), employee_id="synthetic", currency="IDR", submitted_at=now, created_at=now, updated_at=now)
    receipt = Receipt(id=uuid4(), claim_id=claim.id, original_filename="synthetic.pdf", media_type="application/pdf",
                      storage_reference="synthetic", content_hash="0" * 64, created_at=now)
    observed = MockReceiptExtractor().extract(receipt=receipt, content=b"FUTURE_DATE", declared_amount=Decimal("60000"), attempt=1)
    restored = ExtractionResult.model_validate(observed.model_dump(mode="json"))
    assert isinstance(restored.receipt_date.value, str)
    findings = ValidationService(Settings(_env_file=None)).validate(claim=claim, extraction=restored, processing_run_id=uuid4())
    assert any(not item.passed and item.reason_code == "receipt_date_in_future" for item in findings)


def test_agent_acceptance_matrix():
    report = evaluate()
    assert report["total"] >= 12 and report["passed"] == report["total"]
    assert report["false_approvals"] == 0
    assert not report["live_verified"]


def test_policy_api_uses_admin_and_inbox_cannot_access_another_user():
    client = TestClient(app)
    payload = draft().model_dump(mode="json")
    response = client.post("/policies", json=payload)
    assert response.status_code == 201, response.text
    record = response.json()
    published = client.post(f"/policies/{record['id']}/publish", json={"revision": record["revision"]})
    assert published.status_code == 200, published.text
    assert published.headers["cache-control"] == "no-store"
    settings = app.dependency_overrides[get_settings]()
    backend = deps._backend(settings)
    service = NotificationService(backend, settings)
    now = datetime.now(UTC)
    claim = Claim(id=uuid4(), employee_id="employee-a", status="approved", currency="IDR", current_decision_id=uuid4(),
                  submitted_at=now, created_at=now, updated_at=now)
    backend.claims.save(claim)
    service.sync_claim(claim.id)
    foreign_id = service.inbox("employee-a")[0]["id"]
    app.dependency_overrides[get_claim_actor] = lambda: ClaimActor("employee-b")
    assert client.get("/notifications").json()["items"] == []
    assert client.post(f"/notifications/{foreign_id}/read").status_code == 404


def test_inbox_returns_saved_notifications_while_another_claim_is_busy():
    from threading import Event

    settings = app.dependency_overrides[get_settings]()
    backend = deps._backend(settings)
    now = datetime.now(UTC)
    claim = Claim(id=uuid4(), employee_id="test-admin", status="approved", currency="IDR", current_decision_id=uuid4(),
                  submitted_at=now, created_at=now, updated_at=now)
    backend.claims.save(claim)
    NotificationService(backend, settings).sync_claim(claim.id)
    locked, release = Event(), Event()

    def hold_claim():
        with graph_resources(backend, settings).claim_lock(claim.id):
            locked.set()
            assert release.wait(10)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hold_claim)
        assert locked.wait(5)
        try:
            response = TestClient(app).get("/notifications")
            assert response.status_code == 200, response.text
            assert len(response.json()["items"]) == 1
        finally:
            release.set()
        future.result()
