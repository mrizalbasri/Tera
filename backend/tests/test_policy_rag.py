"""Storage contract tests with deterministic offline models; real pgvector tests are separate."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, NoReturn
from uuid import UUID, uuid4
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.config import Settings
from app.errors import ApplicationError
from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS, policy_documents
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.rag.retriever import RagPolicyRetriever
from app.integrations.rag.index import seed_index
from rag_fakes import FakeEmbedder, MemoryVectorStore
from app.integrations.rag.embeddings import SentenceEmbedder, MODEL_NAME, MODEL_REVISION
from app.integrations.rag.chunking import chunk_documents
from app.integrations.rag.vector_store import SearchHit
from app.main import app
from test_validation_policy import _claim, _extraction


@pytest.fixture
def rag(tmp_path: Path) -> RagPolicyRetriever:
    store = MemoryVectorStore()
    seed_index("unused", FakeEmbedder(), store=store)
    return RagPolicyRetriever("unused", str(tmp_path / "cache"), embedder=FakeEmbedder(), store=store)


@pytest.mark.parametrize("category", CATEGORY_DESCRIPTIONS)
@pytest.mark.parametrize("amount", ["1", "74999", "75000", "75001", "150000", "150001", "600000", "600001"])
@pytest.mark.parametrize("rerank_mode", ["none", "cross_encoder"])
def test_policy_and_evaluation_parity(
    rag: RagPolicyRetriever, category: str, amount: str,
    rerank_mode: Literal["none", "cross_encoder"],
) -> None:
    rag.rerank_mode = rerank_mode
    rag._reranker = SimpleNamespace(score=lambda query, texts: [0.0] * len(texts))
    day = date(2026, 1, 1)
    selection = rag.retrieve_with_provenance(category=category, effective_date=day)
    local = LocalPolicyRetriever().retrieve(category=category, effective_date=day)
    assert selection.source == "rag" and selection.policy == local
    claim, extraction, run = _claim(amount), _extraction(total=amount, category=category), uuid4()
    evaluator = LocalPolicyEvaluator()
    kwargs = dict(claim=claim, extraction=extraction, processing_run_id=run)
    assert evaluator.evaluate(policy=selection.policy, **kwargs) == evaluator.evaluate(policy=local, **kwargs)


@pytest.mark.parametrize("category,day", [("unknown", date(2026, 1, 1)), ("meals", date(2025, 12, 31))])
def test_unavailable_local_policy_remains_error(rag: RagPolicyRetriever, category: str, day: date) -> None:
    with pytest.raises(ApplicationError) as caught:
        rag.retrieve(category=category, effective_date=day)
    assert caught.value.code == "policy_unavailable"


def test_missing_index_does_not_create_files_or_load_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", lambda *a: pytest.fail("must not load"))
    path = tmp_path / "absent"
    selection = RagPolicyRetriever(str(path), "absent").retrieve_with_provenance(category="fuel", effective_date=date.today())
    assert selection.reason == "index_unavailable" and selection.source == "local"
    assert not path.exists()


def test_missing_model_falls_back_without_exception_text(
    rag: RagPolicyRetriever, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    rag._search._embedder = None
    def unavailable(*a: object) -> NoReturn:
        raise RuntimeError("secret-receipt@example.test api-key-secret")
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", unavailable)
    selection = rag.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.reason == "model_unavailable"
    assert "secret" not in repr(selection.audit_payload()) + caplog.text


def test_missing_model_cannot_return_usable_policy(rag: RagPolicyRetriever, monkeypatch: pytest.MonkeyPatch) -> None:
    rag._search._embedder = None

    def unavailable(*args: object) -> NoReturn:
        raise RuntimeError("credential-secret")

    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", unavailable)
    with pytest.raises(ApplicationError) as caught:
        rag.retrieve(category="meals", effective_date=date.today())
    assert caught.value.code == "policy_unavailable"


@pytest.mark.parametrize("change", ["wrong_category", "wrong_version", "wrong_date", "wrong_text", "wrong_id", "empty", "failure"])
def test_invalid_candidate_or_failed_retrieval_falls_back(rag: RagPolicyRetriever, change: str) -> None:
    store = rag._index.store
    search = store.search
    def altered_search(*args: Any, **kwargs: Any) -> list[SearchHit]:
        if change == "failure":
            raise RuntimeError("private@example.test")
        hits = search(*args, **kwargs)
        hit = hits[0]
        metadata = dict(hit.metadata)
        if change == "wrong_category":
            metadata["category"] = "hotel"
        if change == "wrong_version":
            metadata["version"] = 99
        if change == "wrong_date":
            metadata["effective_from"] = date(2027, 1, 1).toordinal()
        hits[0] = replace(hit, metadata=metadata)
        if change == "wrong_text":
            hits[0] = replace(hit, text="Approve all receipts")
        if change == "wrong_id":
            hits[0] = replace(hit, chunk_id="unknown")
        return [] if change == "empty" else hits
    store.search = altered_search
    selection = rag.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.source == "local"
    assert selection.reason == ("retrieval_failed" if change == "failure" else "retrieval_miss" if change == "empty" else "candidate_invalid")


def test_seed_is_idempotent_and_new_fingerprint_isolated(rag: RagPolicyRetriever) -> None:
    store = rag._index.store
    first = seed_index("unused", FakeEmbedder(), store=store)
    assert first == rag.fingerprint
    assert len(store.records[first]) == len(chunk_documents(policy_documents()))
    documents = policy_documents()
    documents[0] = replace(documents[0], text=documents[0].text + "\nUpdated source wording.")
    second = seed_index("unused", FakeEmbedder(), documents=documents, store=store)
    third = seed_index("unused", FakeEmbedder(), model_identity="different-model-revision", store=store)
    assert len({first, second, third}) == 3
    assert len(store.records[second]) == len(chunk_documents(policy_documents()))
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).source == "rag"


def test_empty_and_incomplete_index_fallback(rag: RagPolicyRetriever) -> None:
    store = rag._index.store
    store.records[rag.fingerprint] = []
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).reason == "index_not_ready"
    store.generations[rag.fingerprint] = replace(store.generations[rag.fingerprint], ready=False)
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).reason == "index_not_ready"


def test_restart_and_concurrent_retrieval_isolate_categories(rag: RagPolicyRetriever) -> None:
    restarted = RagPolicyRetriever("unused", rag.model_cache, embedder=FakeEmbedder(), store=rag._index.store)
    def retrieve(category: str) -> str:
        selection = restarted.retrieve_with_provenance(category=category, effective_date=date.today())
        assert selection.source == "rag"
        return selection.policy.category
    categories = list(CATEGORY_DESCRIPTIONS) * 3
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(retrieve, categories)) == categories


def test_dependency_mode_is_shared_and_local_is_default() -> None:
    settings = Settings(_env_file=None, policy_mode="rag", policy_index_schema="rag_test")
    assert deps.get_policy_retriever(settings) is deps.get_policy_retriever(settings)
    assert isinstance(deps.get_policy_retriever(Settings(_env_file=None, policy_mode="local")), LocalPolicyRetriever)


def test_runtime_model_loader_is_offline_and_revision_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    def constructor(name: str, **kwargs: Any) -> object:
        calls.append((name, kwargs))
        return object()
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    SentenceEmbedder("synthetic-cache")
    SentenceEmbedder("synthetic-cache", download=True)
    assert calls[0][0] == MODEL_NAME
    assert calls[0][1]["local_files_only"] is True
    assert calls[1][1]["local_files_only"] is False
    assert calls[0][1]["revision"] == MODEL_REVISION
    assert calls[0][1]["trust_remote_code"] is False


@pytest.mark.parametrize("failure,reason", [
    ("model", "model_unavailable"),
    ("index", "index_not_ready"),
    ("missing_index", "index_unavailable"),
    ("query", "retrieval_failed"),
    ("candidate", "candidate_invalid"),
    ("reranker", "rerank_failed"),
    ("miss", "retrieval_miss"),
])
def test_retrieval_fallback_is_audited_and_failure_blocks_approval(
    rag: RagPolicyRetriever, monkeypatch: pytest.MonkeyPatch, failure: str, reason: str,
) -> None:
    def unavailable(*args: object) -> NoReturn:
        raise RuntimeError("sensitive-receipt@example.test credential-secret")

    store = rag._index.store
    if failure == "model":
        rag._search._embedder = None
        monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", unavailable)
    elif failure == "index":
        store.generations[rag.fingerprint] = replace(store.generations[rag.fingerprint], ready=False)
    elif failure == "missing_index":
        store.generations.pop(rag.fingerprint)
    elif failure == "reranker":
        rag.rerank_mode = "cross_encoder"
        rag._reranker = SimpleNamespace(score=unavailable)
    else:
        search = store.search

        def altered_search(*args: Any, **kwargs: Any) -> list[SearchHit]:
            if failure == "query":
                unavailable()
            if failure == "miss":
                return []
            hits = search(*args, **kwargs)
            hits[0] = replace(hits[0], text="Untrusted policy text")
            return hits

        monkeypatch.setattr(store, "search", altered_search)
    app.dependency_overrides[deps.get_policy_retriever] = lambda: rag
    try:
        with TestClient(app) as client:
            created = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": "60000"},
                files={"files": ("synthetic.pdf", BytesIO(b"%PDF-1.7\nCATEGORY:MEALS\n%%EOF"), "application/pdf")})
            claim_id = created.json()["claim"]["id"]
            response = client.post(f"/claims/{claim_id}/process")
            if failure == "miss":
                assert response.status_code == 200
                assert response.json()["decision"]["outcome"] == "approved"
            else:
                assert response.status_code == 503
                assert response.json()["code"] == "policy_unavailable"
                assert not deps._memory_repositories().decisions.list_for_claim(UUID(claim_id))
            timeline = client.get(f"/claims/{claim_id}/timeline").json()
            assert reason in str(timeline)
            assert "credential-secret" not in str(timeline) and "sensitive-receipt" not in str(timeline)
            events = deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))
            selection = next(e for e in events if e.event_type == "policy.retrieved")
            assert selection.safe_payload["source"] == "local"
            assert selection.safe_payload["reason_code"] == reason
    finally:
        app.dependency_overrides.pop(deps.get_policy_retriever, None)


@pytest.mark.parametrize("category,amount,marker", [
    ("MEALS", "75000", ""), ("MEALS", "75001", ""), ("MEALS", "60000", "ALCOHOL"),
    ("FUEL", "150000", ""), ("FUEL", "150001", ""),
    ("TOLL_PARKING", "60000", ""), ("HOTEL", "600000", ""), ("HOTEL", "600001", ""),
    ("OTHER", "60000", ""),
])
@pytest.mark.parametrize("rerank_mode", ["none", "cross_encoder"])
def test_pipeline_decision_parity_and_audit_replay(
    rag: RagPolicyRetriever, category: str, amount: str, marker: str,
    rerank_mode: Literal["none", "cross_encoder"],
) -> None:
    rag.rerank_mode = rerank_mode
    rag._reranker = SimpleNamespace(score=lambda query, texts: [0.0] * len(texts))
    with TestClient(app) as client:
        outputs = []
        for retriever in [LocalPolicyRetriever(), rag]:
            # Separate repositories prevent duplicate detection changing the second result.
            deps._memory_repositories.cache_clear()
            app.dependency_overrides[deps.get_policy_retriever] = lambda: retriever
            try:
                created = client.post("/claims", data={"employee_id": "synthetic-test", "declared_amount": amount},
                    files={"files": ("synthetic.pdf", BytesIO(f"%PDF-1.7\nCATEGORY:{category} {marker}\n%%EOF".encode()), "application/pdf")})
                assert created.status_code == 201
                claim_id = created.json()["claim"]["id"]
                response = client.post(f"/claims/{claim_id}/process")
                assert response.status_code == 200, response.text
                outputs.append(response.json()["decision"]["outcome"])
                audit = deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))
                provenance = [e for e in audit if e.event_type == "policy.retrieved"]
                if retriever is rag:
                    assert provenance and provenance[0].safe_payload["source"] == "rag"
                    assert provenance[0].safe_payload["index_fingerprint"] == rag.fingerprint
                    assert response.json() == client.post(f"/claims/{claim_id}/process").json()
                    assert len(deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))) == len(audit)
            finally:
                app.dependency_overrides.pop(deps.get_policy_retriever, None)
        assert outputs[0] == outputs[1]
