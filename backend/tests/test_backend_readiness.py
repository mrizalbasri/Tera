"""Operational regressions use synthetic receipts and disposable databases."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text

from app.api import deps
from app.api.auth import require_admin, require_session
from app.api.claim_access import ClaimActor, get_claim_actor
from app.agent.nodes import ClaimNodes
from app.agent.runtime import GraphResources, close_graph_resources
from app.config import Settings, get_settings
from app.errors import ApplicationError
from app.main import app
from app.repositories.migrations import CURRENT_VERSION, require_current, schema_version, upgrade
from app.repositories.query import ClaimFilter
from app.repositories.sql import SqlRepositories
from app.schemas.core import Claim
from app.services.recovery import build_processing
from app.services.reporting import ReportingService


@pytest.fixture(params=["sqlite", "postgres"])
def persistent(request, tmp_path):
    url = request.getfixturevalue("postgres_database_url") if request.param == "postgres" else f"sqlite:///{tmp_path / 'claims.db'}"
    settings = Settings(_env_file=None, storage_backend="sql", database_url=url,
                        graph_checkpoint_path=str(tmp_path / "graph.db"))
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def create(client, marker="normal", amount="60000"):
    response = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": amount},
                           files={"files": ("synthetic.pdf", BytesIO(f"%PDF-1.7\n{marker}".encode()), "application/pdf")})
    assert response.status_code == 201, response.text
    return UUID(response.json()["claim"]["id"])


@pytest.mark.parametrize("after_commit", [False, True])
def test_restart_recovers_interrupted_node_without_duplicate_records(persistent, monkeypatch, after_commit):
    client = TestClient(app)
    claim_id = create(client)
    original = ClaimNodes.validate
    calls = []

    def crash_inside(self, state):
        calls.append("validate")
        result = original(self, state)
        if not after_commit:
            raise RuntimeError("synthetic crash")
        return result

    monkeypatch.setattr(ClaimNodes, "validate", crash_inside)
    original_step = GraphResources.run_step

    def crash_after(self, name, state, action):
        result = original_step(self, name, state, action)
        if after_commit and name == "validate":
            raise RuntimeError("synthetic crash")
        return result

    monkeypatch.setattr(GraphResources, "run_step", crash_after)
    with pytest.raises(RuntimeError, match="synthetic crash"):
        client.post(f"/claims/{claim_id}/process", headers={"Idempotency-Key": "recover"})
    backend = deps._backend(persistent)
    assert backend.runs.latest_for_claim(claim_id).status == "running"
    saved_findings = backend.findings.list_for_claim(claim_id)
    assert bool(saved_findings) == after_commit
    monkeypatch.setattr(ClaimNodes, "validate", original)
    monkeypatch.setattr(GraphResources, "run_step", original_step)
    close_graph_resources()
    deps.close_sql_repositories()
    processed = client.post(f"/claims/{claim_id}/process", headers={"Idempotency-Key": "recover"})
    assert processed.status_code == 200, processed.text
    assert processed.json()["claim"]["status"] == "approved"
    backend = deps._backend(persistent)
    assert len(backend.runs.list_for_claim(claim_id)) == 1
    assert len(backend.attempts.list_for_claim(claim_id)) == 1
    assert len(backend.decisions.list_for_claim(claim_id)) == 1
    findings = backend.findings.list_for_claim(claim_id)
    assert len({f.rule_id for f in findings}) == len(findings)
    if after_commit:
        assert len(findings) == len(saved_findings)
    assert client.post(f"/claims/{claim_id}/process").json() == processed.json()


def test_crash_after_decision_commit_replays_single_decision(persistent, monkeypatch):
    client = TestClient(app)
    claim_id = create(client)
    original = GraphResources.run_step

    def crash(self, name, state, action):
        result = original(self, name, state, action)
        if name == "decide":
            raise RuntimeError("synthetic exit before checkpoint")
        return result

    monkeypatch.setattr(GraphResources, "run_step", crash)
    with pytest.raises(RuntimeError):
        client.post(f"/claims/{claim_id}/process")
    monkeypatch.setattr(GraphResources, "run_step", original)
    close_graph_resources()
    deps.close_sql_repositories()
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "approved"
    assert len(deps._backend(persistent).decisions.list_for_claim(claim_id)) == 1


def test_sql_transaction_rolls_back_claim_receipt_and_key(persistent, monkeypatch):
    backend = deps._backend(persistent)

    def crash(*args, **kwargs):
        raise RuntimeError("synthetic storage failure")

    monkeypatch.setattr(backend.receipts, "save", crash)
    with pytest.raises(RuntimeError):
        TestClient(app).post("/claims", data={"employee_id": "synthetic"},
                             headers={"Idempotency-Key": "atomic"},
                             files={"files": ("x.pdf", b"%PDF-1.7\natomic", "application/pdf")})
    assert backend.claims.count(ClaimFilter()) == 0
    assert backend.claims.get_by_idempotency_key("atomic") is None
    with backend._engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM file_storage")) == 0


def test_migration_is_repeatable_preserves_existing_data_and_checks_version(persistent):
    backend = deps._backend(persistent)
    claim_id = create(TestClient(app))
    upgrade(backend._engine)
    upgrade(backend._engine)
    assert backend.claims.get(claim_id) is not None
    with backend._engine.begin() as connection:
        assert schema_version(connection) == CURRENT_VERSION
        connection.execute(text("DELETE FROM schema_migrations WHERE version = :version"), {"version": CURRENT_VERSION})
    with pytest.raises(RuntimeError, match="not current"):
        SqlRepositories(persistent.database_url, initialize_schema=False)
    upgrade(backend._engine)
    require_current(backend._engine)


def test_legacy_sqlite_migration_keeps_payload_and_adds_order(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE claims (id VARCHAR(36) PRIMARY KEY, employee_id VARCHAR(100), status VARCHAR(40), payload JSON)"))
        connection.execute(text("INSERT INTO claims VALUES ('legacy', 'synthetic', 'received', '{}')"))
    upgrade(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT employee_id FROM claims WHERE id = 'legacy'")) == "synthetic"
        assert "insertion_order" in {c["name"] for c in inspect(connection).get_columns("claims")}
    engine.dispose()


def test_pagination_filters_ownership_and_total(persistent):
    backend = deps._backend(persistent)
    now = datetime.now(UTC)
    for index in range(7):
        backend.claims.save(Claim(id=uuid4(), employee_id="owner" if index < 5 else "other",
                                 status="received", submitted_at=now + timedelta(days=index), currency="IDR",
                                 created_at=now, updated_at=now))
    app.dependency_overrides[get_claim_actor] = lambda: ClaimActor("owner")
    client = TestClient(app)
    first = client.get("/claims?limit=2&employee_id=other").json()
    second = client.get("/claims?limit=2&offset=2").json()
    assert first["total"] == second["total"] == 5
    assert len(first["items"]) == len(second["items"]) == 2
    assert not {c["id"] for c in first["items"]} & {c["id"] for c in second["items"]}
    filtered = client.get("/claims", params={"period_from": (now + timedelta(days=3)).date().isoformat()}).json()
    assert filtered["total"] == 2
    for query in ("limit=201", "limit=0", "offset=-1", "status=garbage", "period_from=2026-12-01&period_to=2026-01-01"):
        assert client.get(f"/claims?{query}").status_code == 422


def test_reporting_batches_and_pending_is_not_automated(persistent):
    client = TestClient(app)
    for marker in ("one", "two", "three"):
        create(client, marker)
    backend = deps._backend(persistent)
    calls = []
    event.listen(backend._engine, "before_cursor_execute", lambda *args: calls.append(args[2]))
    summary = client.get("/reports/summary")
    assert summary.status_code == 200
    assert summary.json()["automated_claims"] == 0
    assert summary.json()["estimated_time_saved_minutes"] == 0
    # Count is independent of the number of claims in one batch.
    assert len(calls) <= 5
    assert client.get("/reports/claims.csv?period_from=2026-12-01&period_to=2026-01-01").status_code == 422


def test_csv_streams_batches_and_escapes_formulas():
    backend = deps._memory_repositories()
    now = datetime.now(UTC)
    for index in range(5):
        backend.claims.save(Claim(id=uuid4(), employee_id="=1+1", currency="IDR", submitted_at=now, created_at=now, updated_at=now))
    reporting = ReportingService(backend.claims)
    reporting.BATCH_SIZE = 2
    chunks = list(reporting.csv_rows(ClaimFilter()))
    assert len(chunks) == 4
    assert "'=1+1" in "".join(chunks)


@pytest.mark.parametrize("kwargs,expected", [
    ({"max_receipts_per_claim": 1}, "too_many_receipts"),
    ({"max_upload_total_bytes": 15}, "upload_too_large"),
    ({"max_request_bytes": 20}, "request_too_large"),
])
def test_upload_limits(kwargs, expected):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, **kwargs)
    response = TestClient(app).post("/claims", data={"employee_id": "synthetic"}, files=[
        ("files", ("one.pdf", b"%PDF-1.7\none", "application/pdf")),
        ("files", ("two.pdf", b"%PDF-1.7\ntwo", "application/pdf")),
    ])
    assert response.status_code in (413, 422)
    assert response.json()["code"] == expected
    assert deps._memory_repositories().claims.count(ClaimFilter()) == 0


def test_chunked_request_limit_without_content_length():
    settings = Settings(_env_file=None, max_request_bytes=12)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post("/claims", headers={"Content-Type": "multipart/form-data; boundary=x"},
                                    content=iter([b"--x\r\n", b"Content-Disposition: form-data; name=files\r\n\r\n", b"large"]))
    assert response.status_code == 413, response.text
    assert response.json()["code"] == "request_too_large"


def test_rate_limit_is_shared_between_sql_instances(persistent):
    first = SqlRepositories(persistent.database_url)
    second = SqlRepositories(persistent.database_url)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: (first if i % 2 else second).consume_rate_limit("a" * 64, 10, 3), range(10)))
        assert sum(results) == 3
        assert first.consume_rate_limit("a" * 64, 11, 3)
        assert first.consume_rate_limit("b" * 64, 11, 3)
    finally:
        first.close()
        second.close()


def test_http_rate_limit_uses_authenticated_identity_and_retry_after():
    settings = Settings(_env_file=None, rate_limit_write_requests=1)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides.pop(get_claim_actor, None)
    app.dependency_overrides[require_session] = lambda: "synthetic"
    try:
        client = TestClient(app)
        create(client)
        denied = client.post("/claims", files={"files": ("x.pdf", b"%PDF-1.7\nother", "application/pdf")})
        assert denied.status_code == 429
        assert int(denied.headers["Retry-After"]) > 0
        assert client.get("/claims").status_code == 200
        app.dependency_overrides[require_session] = lambda: "another-user"
        assert client.post("/claims", files={"files": ("x.pdf", b"%PDF-1.7\nother", "application/pdf")}).status_code == 201
    finally:
        app.dependency_overrides.pop(require_session, None)


def test_readiness_checks_dependencies_without_exposing_details(persistent, monkeypatch):
    client = TestClient(app)
    assert client.get("/health/ready").json() == {"status": "ready"}
    backend = deps._backend(persistent)

    def broken():
        raise RuntimeError("private password must never appear")

    monkeypatch.setattr(backend, "ready", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert client.get("/health").status_code == 200


PRODUCTION = dict(environment="production", storage_backend="sql",
                  database_url="postgresql+psycopg://tera:synthetic-secret@localhost/tera",
                  provider_mode="live", llm_api_key="synthetic-key", frontend_origin="https://tera.example.test",
                  clerk_issuer="https://synthetic.clerk.accounts.dev", clerk_admin_user_ids="user_synthetic")


@pytest.mark.parametrize("changes", [
    {"storage_backend": "memory"}, {"database_url": "sqlite:///x.db"}, {"provider_mode": "mock"},
    {"llm_api_key": ""}, {"provider_fallback": "mock"}, {"clerk_issuer": ""},
    {"clerk_admin_user_ids": ""}, {"frontend_origin": "http://localhost:5173"},
    {"database_url": "postgresql://tera:change_me@localhost/tera"}, {"demo_mode": True},
])
def test_invalid_production_settings_fail_closed(changes):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **(PRODUCTION | changes))


def test_valid_production_settings():
    assert Settings(_env_file=None, **PRODUCTION).environment == "production"


def test_postgres_lock_excludes_other_process_and_releases(postgres_database_url):
    resources = GraphResources(database_url=postgres_database_url, lock_timeout=0.1)
    claim_id = uuid4()
    script = '''
import os
from app.agent.runtime import GraphResources
from app.errors import ApplicationError
r = GraphResources(database_url=os.environ["SYNTHETIC_TEST_DATABASE"], lock_timeout=0.1)
try:
    with r.claim_lock(os.environ["SYNTHETIC_CLAIM"]):
        print("acquired")
except ApplicationError as error:
    print(error.code)
finally:
    r.close()
'''
    def run():
        result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                                env=dict(os.environ, SYNTHETIC_TEST_DATABASE=postgres_database_url, SYNTHETIC_CLAIM=str(claim_id)),
                                text=True, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()
    try:
        with resources.claim_lock(claim_id):
            with resources.claim_lock(claim_id):
                assert run() == "claim_busy"
        assert run() == "acquired"
    finally:
        resources.close()


WORKER_SCRIPT = '''
import os
import time
from uuid import UUID
from app.config import Settings
Settings.model_config["env_file"] = None
from app.services.recovery import build_processing
from app.agent.nodes import ClaimNodes
from app.integrations.mock import MockReceiptExtractor
settings = Settings(_env_file=None, environment="test", storage_backend="sql",
                    database_url=os.environ["SYNTHETIC_TEST_DATABASE"],
                    graph_checkpoint_path=os.environ["SYNTHETIC_GRAPH_PATH"],
                    provider_mode="mock", policy_mode="local", anomaly_mode="rules")
if os.environ.get("SYNTHETIC_CRASH"):
    original = ClaimNodes.validate
    def crash(self, state):
        original(self, state)
        os._exit(77)
    ClaimNodes.validate = crash
else:
    original = MockReceiptExtractor.extract
    def slow(self, **kwargs):
        time.sleep(0.3)
        return original(self, **kwargs)
    MockReceiptExtractor.extract = slow
outcome = build_processing(settings).process_claim(UUID(os.environ["SYNTHETIC_CLAIM"]))
assert outcome.claim.status == "approved"
print(outcome.decision.id, flush=True)
'''


def worker_environment(settings, claim_id, *, crash=False):
    result = dict(os.environ, SYNTHETIC_TEST_DATABASE=settings.database_url,
                  SYNTHETIC_GRAPH_PATH=settings.graph_checkpoint_path, SYNTHETIC_CLAIM=str(claim_id))
    if crash:
        result["SYNTHETIC_CRASH"] = "1"
    return result


def test_real_process_exit_rolls_back_node_and_recovers(persistent):
    client = TestClient(app)
    claim_id = create(client)
    result = subprocess.run([sys.executable, "-c", WORKER_SCRIPT], cwd=Path(__file__).resolve().parents[1],
                            env=worker_environment(persistent, claim_id, crash=True), capture_output=True, text=True, timeout=30)
    assert result.returncode == 77, result.stderr
    backend = deps._backend(persistent)
    assert backend.runs.latest_for_claim(claim_id).status == "running"
    assert not backend.findings.list_for_claim(claim_id)
    recovery = client.post("/operations/recover")
    assert recovery.status_code == 200, recovery.text
    assert recovery.json()["recovered"] == 1
    assert backend.claims.get(claim_id).status == "approved"
    assert len(backend.runs.list_for_claim(claim_id)) == 1
    assert len(backend.attempts.list_for_claim(claim_id)) == 1
    assert len(backend.decisions.list_for_claim(claim_id)) == 1


def test_two_postgres_workers_process_one_claim_once(postgres_database_url, tmp_path):
    settings = Settings(_env_file=None, storage_backend="sql", database_url=postgres_database_url,
                        graph_checkpoint_path=str(tmp_path / "graph.db"))
    app.dependency_overrides[get_settings] = lambda: settings
    claim_id = create(TestClient(app))
    environment = worker_environment(settings, claim_id)
    processes = [subprocess.Popen([sys.executable, "-c", WORKER_SCRIPT], cwd=Path(__file__).resolve().parents[1],
                                  env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    outputs = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            assert process.returncode == 0, stderr
            outputs.append(stdout.strip())
        assert outputs[0] == outputs[1]
        backend = deps._backend(settings)
        assert len(backend.runs.list_for_claim(claim_id)) == 1
        assert len(backend.decisions.list_for_claim(claim_id)) == 1
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


def test_recovery_does_not_resume_unanswered_clarification(persistent):
    client = TestClient(app)
    claim_id = create(client, "CATEGORY:MEALS shared", "240000")
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "needs_clarification"
    backend = deps._backend(persistent)
    question = backend.clarifications.latest_for_claim(claim_id)
    original_run = backend.runs.latest_for_claim(claim_id)
    # Receipt replacement can move the claim to processing without answering.
    response = client.post(f"/claims/{claim_id}/receipts", files={
        "file": ("clearer.pdf", b"%PDF-1.7\nCATEGORY:MEALS shared clearer", "application/pdf"),
    })
    assert response.status_code == 201, response.text
    assert backend.claims.get(claim_id).status == "processing"
    processing = build_processing(persistent)
    assert processing.recover_claim(claim_id) is None
    assert claim_id not in processing.pending_claim_ids(limit=100)
    assert client.post("/operations/recover").json()["recovered"] == 0
    assert processing.recover_pending()["recovered"] == 0
    assert backend.runs.latest_for_claim(claim_id) == original_run
    assert backend.clarifications.latest_for_claim(claim_id) == question
    assert not backend.context.list_for_claim(claim_id)
    processed = client.post(f"/claims/{claim_id}/process")
    assert processed.status_code == 200, processed.text
    assert processed.json()["claim"]["status"] == "needs_clarification"
    assert client.post(f"/claims/{claim_id}/process?resume=true").status_code == 409
    assert backend.runs.latest_for_claim(claim_id).id != original_run.id
    assert backend.clarifications.list_for_claim(claim_id)[0].status == "cancelled"
    replacement_question = backend.clarifications.latest_for_claim(claim_id)
    answered = client.post(f"/claims/{claim_id}/clarifications/{replacement_question.id}/answer", json={"answer": "4"})
    assert answered.status_code == 200, answered.text
    assert backend.clarifications.latest_for_claim(claim_id).status == "answered"
    assert len(backend.runs.list_for_claim(claim_id)) == 3


def test_answer_and_queued_run_roll_back_together(persistent, monkeypatch):
    from app.services.processing import ClaimProcessingService

    client = TestClient(app)
    claim_id = create(client, "CATEGORY:MEALS shared", "240000")
    client.post(f"/claims/{claim_id}/process")
    backend = deps._backend(persistent)
    question = backend.clarifications.latest_for_claim(claim_id)

    def crash(*args):
        raise RuntimeError("synthetic queue failure")

    monkeypatch.setattr(ClaimProcessingService, "queue_clarification", crash)
    with pytest.raises(RuntimeError, match="synthetic queue failure"):
        client.post(f"/claims/{claim_id}/clarifications/{question.id}/answer", json={"answer": "4"})
    assert backend.clarifications.latest_for_claim(claim_id) == question
    assert backend.claims.get(claim_id).status == "needs_clarification"
    assert len(backend.runs.list_for_claim(claim_id)) == 1
    assert not backend.context.list_for_claim(claim_id)


def test_recovery_after_answer_saved_before_new_run(persistent, monkeypatch):
    from app.services.processing import ClaimProcessingService

    client = TestClient(app)
    claim_id = create(client, "CATEGORY:MEALS shared", "240000")
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "needs_clarification"
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][-1]
    original = ClaimProcessingService.resume_clarification

    def crash(*args):
        raise RuntimeError("synthetic exit after answer commit")

    monkeypatch.setattr(ClaimProcessingService, "resume_clarification", crash)
    with pytest.raises(RuntimeError):
        client.post(f"/claims/{claim_id}/clarifications/{clarification['id']}/answer", json={"answer": "4"})
    monkeypatch.setattr(ClaimProcessingService, "resume_clarification", original)
    assert deps._backend(persistent).runs.latest_for_claim(claim_id).status == "queued"
    response = client.post("/operations/recover")
    assert response.json()["recovered"] == 1, response.text
    backend = deps._backend(persistent)
    assert backend.claims.get(claim_id).status == "approved"
    assert len(backend.context.list_for_claim(claim_id)) == 2
    assert len(backend.runs.list_for_claim(claim_id)) == 2


def test_interrupted_review_requires_admin_retry_and_does_not_duplicate(persistent, monkeypatch):
    from app.services.review import ReviewService

    client = TestClient(app)
    claim_id = create(client, "review", "700000")
    assert client.post(f"/claims/{claim_id}/process").json()["claim"]["status"] == "escalated"
    original = ReviewService._apply_decision

    def crash(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("synthetic review crash")

    monkeypatch.setattr(ReviewService, "_apply_decision", crash)
    with pytest.raises(RuntimeError):
        client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "synthetic review"})
    monkeypatch.setattr(ReviewService, "_apply_decision", original)
    backend = deps._backend(persistent)
    assert backend.claims.get(claim_id).status == "escalated"
    assert len(backend.decisions.list_for_claim(claim_id)) == 1
    assert client.post("/operations/recover").json()["recovered"] == 1
    assert backend.claims.get(claim_id).status == "escalated"
    decision = client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "synthetic retry"})
    assert decision.status_code == 200, decision.text
    assert backend.claims.get(claim_id).status == "approved"
    assert len(backend.decisions.list_for_claim(claim_id)) == 2


def test_background_recovery_worker_scans_and_stops(monkeypatch):
    from threading import Event
    from app.services import recovery

    scanned = Event()

    class Processing:
        def recover_pending(self):
            scanned.set()
            return {"recovered": 1, "failed": 0}

    monkeypatch.setattr(recovery, "build_processing", lambda settings: Processing())
    worker = recovery.RecoveryWorker(Settings(_env_file=None, recovery_interval_seconds=1))
    worker.start()
    try:
        assert scanned.wait(4)
    finally:
        worker.close()
    assert not worker.thread.is_alive()


def test_operations_are_admin_only():
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides[require_session] = lambda: "synthetic-member"
    try:
        client = TestClient(app)
        assert client.get("/operations/metrics").status_code == 403
        assert client.post("/operations/recover").status_code == 403
    finally:
        app.dependency_overrides.pop(require_session, None)


def test_production_readiness_does_not_create_missing_checkpoint_schema(postgres_database_url):
    url = postgres_database_url
    backend = SqlRepositories(url)
    backend.close()
    settings = Settings(_env_file=None, **(PRODUCTION | {"database_url": url}))
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    engine = create_engine(url)
    try:
        assert "langgraph" not in inspect(engine).get_schema_names()
        with pytest.raises(Exception):
            with TestClient(app):
                pass
    finally:
        engine.dispose()


def test_rolled_back_inner_repository_call_cannot_commit_partial_state(persistent):
    backend = deps._backend(persistent)
    with pytest.raises(RuntimeError, match="rolled back"):
        with backend.transaction() as session:
            session.rollback()
            session.execute(text("INSERT INTO workflow_steps (key, payload) VALUES ('invalid', '{}')"))
    with backend._engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM workflow_steps WHERE key = 'invalid'")) == 0


def test_recovery_attempts_are_bounded(persistent, monkeypatch):
    client = TestClient(app)
    claim_id = create(client)

    def crash(*args):
        raise RuntimeError("synthetic persistent node failure")

    monkeypatch.setattr(ClaimNodes, "validate", crash)
    with pytest.raises(RuntimeError):
        client.post(f"/claims/{claim_id}/process")
    processing = build_processing(persistent)
    for _ in range(persistent.max_recovery_attempts):
        assert processing.recover_pending()["failed"] == 1
    result = processing.recover_pending()
    assert result["failed"] == 1
    run = deps._backend(persistent).runs.latest_for_claim(claim_id)
    assert run.status == "failed"
    assert run.error_code == "recovery_exhausted"
    assert processing.recover_pending()["scanned"] == 0


def test_migration_and_recovery_commands_use_isolated_settings(persistent, monkeypatch, capsys):
    import app.migrate as migration
    from app import config
    from app.services import recovery

    monkeypatch.setattr(migration, "get_settings", lambda: persistent)
    migration.main()
    assert "migrations complete" in capsys.readouterr().out
    monkeypatch.setattr(config, "get_settings", lambda: persistent)
    monkeypatch.setattr(sys, "argv", ["recovery", "--limit", "10"])
    recovery.main()
    assert '"scanned": 0' in capsys.readouterr().out


@pytest.mark.parametrize("marker,amount,node,action", [
    ("CATEGORY:MEALS shared", "240000", "decide", "answer"),
    ("review", "700000", "decide", "review"),
    ("LOW_CONFIDENCE", "60000", "extract", "answer"),
])
def test_waiting_input_after_terminal_commit_before_checkpoint(persistent, monkeypatch, marker, amount, node, action):
    client = TestClient(app)
    claim_id = create(client, marker, amount)
    original = GraphResources.run_step

    def crash(self, name, state, operation):
        result = original(self, name, state, operation)
        if name == node:
            raise RuntimeError("synthetic crash before waiting checkpoint")
        return result

    monkeypatch.setattr(GraphResources, "run_step", crash)
    with pytest.raises(RuntimeError):
        client.post(f"/claims/{claim_id}/process")
    monkeypatch.setattr(GraphResources, "run_step", original)
    close_graph_resources()
    deps.close_sql_repositories()
    if action == "review":
        response = client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "synthetic review"})
    else:
        question = client.get(f"/claims/{claim_id}/clarifications").json()["items"][-1]
        response = client.post(f"/claims/{claim_id}/clarifications/{question['id']}/answer", json={"answer": "4"})
    assert response.status_code == 200, response.text
    assert len(deps._backend(persistent).runs.list_for_claim(claim_id)) == 2


def test_outdated_clarification_cannot_mutate_claim(persistent):
    client = TestClient(app)
    claim_id = create(client, "CATEGORY:MEALS shared", "240000")
    client.post(f"/claims/{claim_id}/process")
    backend = deps._backend(persistent)
    old = backend.clarifications.latest_for_claim(claim_id)
    newer = old.model_copy(update={"id": uuid4(), "created_at": datetime.now(UTC)})
    backend.clarifications.save(newer)
    response = client.post(f"/claims/{claim_id}/clarifications/{old.id}/answer", json={"answer": "4"})
    assert response.status_code == 409
    assert backend.claims.get(claim_id).status == "needs_clarification"
    assert len(backend.context.list_for_claim(claim_id)) == 0
    assert next(c for c in backend.clarifications.list_for_claim(claim_id) if c.id == old.id).status == "open"


def test_failed_sql_node_keeps_diagnostic_attempt_and_failure_audit(persistent):
    class FailingExtractor:
        def extract(self, **kwargs):
            raise ApplicationError("provider_timeout", "Synthetic timeout.", 502)

    app.dependency_overrides[deps.get_receipt_extractor] = lambda: FailingExtractor()
    try:
        client = TestClient(app)
        claim_id = create(client)
        response = client.post(f"/claims/{claim_id}/process", headers={"Idempotency-Key": "failure"})
        assert response.status_code == 502
        backend = deps._backend(persistent)
        assert backend.runs.latest_for_claim(claim_id).status == "failed"
        attempts = backend.attempts.list_for_claim(claim_id)
        assert len(attempts) == 1
        assert attempts[0].error_code == "provider_timeout"
        events = backend.audit.list_for_aggregate("claim", claim_id)
        assert sum(e.event_type == "processing_run.completed" for e in events) == 1
        assert client.post(f"/claims/{claim_id}/process", headers={"Idempotency-Key": "failure"}).status_code == 502
        assert len(backend.attempts.list_for_claim(claim_id)) == 1
    finally:
        app.dependency_overrides.pop(deps.get_receipt_extractor, None)
