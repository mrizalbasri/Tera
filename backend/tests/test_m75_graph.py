"""M7.5 contract: real graphs and checkpoints, deterministic model fixtures."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import subprocess
import sys
import os
from threading import Barrier
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.agent.runtime import close_graph_resources, graph_resources
from app.main import app


@pytest.fixture(params=["memory", "sql", "postgres"])
def graph_env(request, tmp_path):
    database_url = (request.getfixturevalue("postgres_database_url") if request.param == "postgres"
                    else f"sqlite:///{tmp_path / 'claims.db'}")
    settings = Settings(
        _env_file=None, provider_mode="mock",
        storage_backend="memory" if request.param == "memory" else "sql",
        database_url=database_url,
        graph_checkpoint_path=str(tmp_path / "graph.db"),
        llm_api_key="private-test-credential",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, settings
    app.dependency_overrides.pop(get_settings, None)


def create(client, amount="60000", marker="ordinary"):
    response = client.post(
        "/claims", data={"employee_id": "private-employee@example.test", "declared_amount": amount},
        files={"files": ("private-receipt.pdf",
                         BytesIO(f"%PDF-1.7\n{marker}\n%%EOF".encode()), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["claim"]["id"]


def process(client, claim_id):
    response = client.post(f"/claims/{claim_id}/process")
    assert response.status_code == 200, response.text
    return response.json()


def answer(client, claim_id, text="4"):
    clarification = client.get(f"/claims/{claim_id}/clarifications").json()["items"][-1]
    return client.post(
        f"/claims/{claim_id}/clarifications/{clarification['id']}/answer",
        json={"answer": text, "answered_by": "private-responder@example.test"},
    )


def review(client, claim_id, action="approve"):
    return client.post(f"/reviews/{claim_id}/decision", json={
        "action": action, "reason": "private-review-reason@example.test",
        "reviewer_reference": "private-reviewer@example.test",
    })


def records(settings):
    return deps._backend(settings)


def checkpoint(settings, claim_id):
    saver = graph_resources(records(settings), settings).saver
    return saver.get_tuple({"configurable": {"thread_id": claim_id}})


def restart(settings):
    if settings.storage_backend != "sql":
        return
    close_graph_resources()
    deps.close_sql_repositories()


@pytest.mark.parametrize("amount,marker,outcome,stage", [
    ("60000", "CATEGORY:MEALS normal", "approved", "__end__"),
    ("700000", "hotel-review", "escalated", "wait_review"),
    ("240000", "CATEGORY:MEALS shared", "needs_clarification", "wait_clarification"),
    ("60000", "LOW_CONFIDENCE", "needs_clarification", "wait_clarification"),
])
def test_graph_routes_preserve_business_outcomes(graph_env, amount, marker, outcome, stage):
    client, settings = graph_env
    claim_id = create(client, amount, marker)
    result = process(client, claim_id)
    assert result["claim"]["status"] == outcome
    saved = checkpoint(settings, claim_id)
    assert saved.checkpoint["channel_values"]["stage"] == stage
    before = client.get(f"/claims/{claim_id}/timeline").json()
    assert process(client, claim_id) == result
    assert client.get(f"/claims/{claim_id}/timeline").json() == before
    assert len(records(settings).runs.list_for_claim(UUID(claim_id))) == 1


def test_clarification_survives_restart_and_resumes_exactly_once(graph_env):
    client, settings = graph_env
    claim_id = create(client, "240000", "CATEGORY:MEALS shared")
    process(client, claim_id)
    initial = records(settings).runs.latest_for_claim(UUID(claim_id))
    restart(settings)
    result = answer(client, claim_id)
    assert result.status_code == 200, result.text
    assert result.json()["claim"]["status"] == "approved"
    runs = records(settings).runs.list_for_claim(UUID(claim_id))
    assert len(runs) == 2 and runs[0].id == initial.id
    assert runs[0].status == "needs_clarification" and runs[1].status == "succeeded"
    before = client.get(f"/claims/{claim_id}/timeline").json()
    assert answer(client, claim_id, "1").json()["decision"] == result.json()["decision"]
    assert client.get(f"/claims/{claim_id}/timeline").json() == before
    assert len(records(settings).context.list_for_claim(UUID(claim_id))) == 2


@pytest.mark.parametrize("action,outcome", [("approve", "approved"), ("reject", "rejected")])
def test_review_survives_restart_with_new_run_without_extraction(graph_env, action, outcome):
    client, settings = graph_env
    claim_id = create(client, "700000", "review me")
    original = process(client, claim_id)
    initial_attempts = len(client.get(f"/claims/{claim_id}").json()["attempts"])
    restart(settings)

    class NeverExtract:
        def extract(self, **kwargs):
            pytest.fail("human review must not call the model again")

    app.dependency_overrides[deps.get_receipt_extractor] = lambda: NeverExtract()
    try:
        response = review(client, claim_id, action)
        assert response.status_code == 200, response.text
        decision = response.json()["decision"]
        assert decision["outcome"] == outcome and decision["created_by"] == "reviewer"
        assert decision["processing_run_id"] != original["decision"]["processing_run_id"]
        assert decision["source_signal_ids"] == original["decision"]["source_signal_ids"]
        runs = records(settings).runs.list_for_claim(UUID(claim_id))
        assert [r.status for r in runs] == ["escalated", "succeeded"]
        assert review(client, claim_id, action).status_code == 409
        detail = client.get(f"/claims/{claim_id}").json()
        assert len(detail["decisions"]) == 2 and len(detail["attempts"]) == initial_attempts
        assert process(client, claim_id)["decision"] == decision
    finally:
        app.dependency_overrides.pop(deps.get_receipt_extractor, None)


@pytest.mark.parametrize("kind", ["clarification", "review"])
def test_pre_graph_waiting_claims_are_bootstrapped_without_duplicate_records(graph_env, kind):
    client, settings = graph_env
    claim_id = create(client, "240000" if kind == "clarification" else "700000",
                      "CATEGORY:MEALS legacy" if kind == "clarification" else "legacy review")
    process(client, claim_id)
    resources = graph_resources(records(settings), settings)
    resources.saver.delete_thread(claim_id)
    assert checkpoint(settings, claim_id) is None
    response = answer(client, claim_id) if kind == "clarification" else review(client, claim_id)
    assert response.status_code == 200, response.text
    assert response.json()["claim"]["status"] == "approved"
    repo = records(settings)
    assert len(repo.runs.list_for_claim(UUID(claim_id))) == 2
    assert len(repo.reviews.list_for_claim(UUID(claim_id))) == (kind == "review")
    assert len(repo.clarifications.list_for_claim(UUID(claim_id))) == (kind == "clarification")


def test_concurrent_clarification_answers_and_claim_isolation(graph_env):
    client, settings = graph_env
    first = create(client, "240000", "CATEGORY:MEALS first")
    second = create(client, "700000", "second")
    process(client, first)
    process(client, second)
    with ThreadPoolExecutor(max_workers=4) as pool:
        replies = list(pool.map(lambda _: answer(client, first), range(4)))
    assert all(r.status_code == 200 for r in replies)
    assert len({r.json()["decision"]["id"] for r in replies}) == 1
    repo = records(settings)
    assert len(repo.runs.list_for_claim(UUID(first))) == 2
    assert len(repo.runs.list_for_claim(UUID(second))) == 1
    assert checkpoint(settings, second).checkpoint["channel_values"]["stage"] == "wait_review"
    assert checkpoint(settings, first).checkpoint["channel_values"]["stage"] == "__end__"
    events = repo.audit.list_for_aggregate("claim", UUID(first))
    assert sum(e.event_type == "clarification.answered" for e in events) == 1
    assert sum(e.event_type == "processing_run.completed" for e in events) == 2


def test_concurrent_reviews_only_apply_one_decision(graph_env):
    client, settings = graph_env
    claim_id = create(client, "700000", "concurrent reviews")
    process(client, claim_id)
    with ThreadPoolExecutor(max_workers=3) as pool:
        replies = list(pool.map(lambda _: review(client, claim_id), range(3)))
    assert sorted(r.status_code for r in replies) == [200, 409, 409]
    assert len(records(settings).runs.list_for_claim(UUID(claim_id))) == 2
    assert len(records(settings).decisions.list_for_claim(UUID(claim_id))) == 2


@pytest.mark.parametrize("kind", ["review", "clarification"])
def test_checkpoint_history_contains_only_control_data(graph_env, kind):
    client, settings = graph_env
    claim_id = create(
        client, "700000" if kind == "review" else "240000",
        ("CATEGORY:MEALS " if kind == "clarification" else "")
        + "private-receipt-content@example.test",
    )
    process(client, claim_id)
    response = (review(client, claim_id) if kind == "review"
                else answer(client, claim_id, "4 private-answer@example.test"))
    assert response.status_code == 200
    saver = graph_resources(records(settings), settings).saver
    history = list(saver.list({"configurable": {"thread_id": claim_id}}))
    assert len(history) > 6, "each step must actually be checkpointed"
    serialized = repr(history)
    assert "private-" not in serialized
    assert "%PDF" not in serialized
    for item in history:
        values = item.checkpoint["channel_values"]
        for key in ("claim_id", "run_id", "pipeline_version", "stage"):
            if key in values:
                assert isinstance(values[key], str)
    if settings.storage_backend == "sql" and settings.database_url.startswith("sqlite"):
        raw = Path(settings.graph_checkpoint_path).read_bytes()
        assert b"private-" not in raw and b"%PDF" not in raw


def test_shared_service_keeps_concurrent_review_inputs_isolated(graph_env, monkeypatch):
    client, settings = graph_env
    instances = []
    service_type = deps.ClaimProcessingService

    def capture(*args, **kwargs):
        service = service_type(*args, **kwargs)
        instances.append(service)
        return service

    monkeypatch.setattr(deps, "ClaimProcessingService", capture)
    first = create(client, "700000", "first concurrent review")
    second = create(client, "750000", "second concurrent review")
    process(client, first)
    process(client, second)
    shared = instances[0]
    rendezvous = Barrier(2)
    invoke = shared.graph.invoke

    def concurrent_invoke(*args, **kwargs):
        rendezvous.wait(timeout=10)
        return invoke(*args, **kwargs)

    monkeypatch.setattr(shared.graph, "invoke", concurrent_invoke)
    app.dependency_overrides[deps.get_extraction_service] = lambda: shared
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            approved = pool.submit(review, client, first, "approve")
            rejected = pool.submit(review, client, second, "reject")
            results = [approved.result(), rejected.result()]
        assert [r.status_code for r in results] == [200, 200]
        assert [r.json()["decision"]["outcome"] for r in results] == ["approved", "rejected"]
        assert [r.json()["decision"]["claim_id"] for r in results] == [first, second]
    finally:
        app.dependency_overrides.pop(deps.get_extraction_service, None)


def test_classified_errors_end_run_and_new_attempt_can_start(graph_env):
    client, settings = graph_env
    claim_id = create(client, marker="MALFORMED")
    for _ in range(2):
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 502
        assert response.json()["code"] == "malformed_extraction"
    assert [r.status for r in records(settings).runs.list_for_claim(UUID(claim_id))] == ["failed", "failed"]


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
@pytest.mark.parametrize("kind", ["clarification", "review"])
def test_sql_resume_across_separate_python_processes(tmp_path, kind, backend, request):
    database_url = (request.getfixturevalue("postgres_database_url") if backend == "postgres"
                    else f"sqlite:///{tmp_path / 'claims.db'}")
    script = r'''
import sys
import os
from pathlib import Path
from app.config import Settings, get_settings
Settings.model_config["env_file"] = None
from app.main import app
from fastapi.testclient import TestClient

directory, kind, phase, claim_id = sys.argv[1:]
settings = Settings(
    _env_file=None, storage_backend="sql", provider_mode="mock",
    database_url=os.environ["CLAIM_TEST_DATABASE_URL"],
    graph_checkpoint_path=str(Path(directory) / "graph.db"),
)
app.dependency_overrides[get_settings] = lambda: settings
from app.api.auth import require_admin
app.dependency_overrides[require_admin] = lambda: "synthetic"
from app.api.claim_access import ClaimActor, get_claim_actor
app.dependency_overrides[get_claim_actor] = lambda: ClaimActor("synthetic", admin=True, demo=True)
with TestClient(app) as client:
    if phase == "pause":
        shared = kind == "clarification"
        created = client.post(
            "/claims", data={"employee_id": "synthetic", "declared_amount": "240000" if shared else "700000"},
            files={"files": ("synthetic.pdf", b"%PDF-1.7\nCATEGORY:MEALS" if shared else b"%PDF-1.7\nreview", "application/pdf")},
        )
        assert created.status_code == 201, created.status_code
        claim_id = created.json()["claim"]["id"]
        response = client.post(f"/claims/{claim_id}/process")
        assert response.status_code == 200, response.status_code
        assert response.json()["claim"]["status"] == ("needs_clarification" if shared else "escalated")
        print(claim_id)
    else:
        if kind == "clarification":
            question = client.get(f"/claims/{claim_id}/clarifications").json()["items"][-1]
            response = client.post(f"/claims/{claim_id}/clarifications/{question['id']}/answer",
                                   json={"answer": "4", "answered_by": "synthetic"})
        else:
            response = client.post(f"/reviews/{claim_id}/decision",
                                   json={"action": "approve", "reason": "synthetic review", "reviewer_reference": "synthetic"})
        assert response.status_code == 200, response.status_code
        assert response.json()["claim"]["status"] == "approved"
        from app.api.deps import _backend
        from uuid import UUID
        assert len(_backend(settings).runs.list_for_claim(UUID(claim_id))) == 2
        print("resumed")
'''
    def run(phase, claim_id=""):
        result = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path), kind, phase, claim_id],
            cwd=Path(__file__).resolve().parents[1], capture_output=True,
            text=True, timeout=30,
            env=dict(os.environ, CLAIM_TEST_DATABASE_URL=database_url),
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    claim_id = run("pause")
    assert run("resume", claim_id) == "resumed"
