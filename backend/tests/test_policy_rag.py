"""Real Chroma, deterministic embeddings, no model downloads or provider calls."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from io import BytesIO
from uuid import UUID, uuid4
from types import SimpleNamespace
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.config import Settings
from app.errors import ApplicationError
from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS, policy_documents
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.rag.retriever import RagPolicyRetriever
from app.integrations.rag.index import chroma_client, collection_name, seed_index
from app.integrations.rag.embeddings import SentenceEmbedder, MODEL_NAME, MODEL_REVISION
from app.integrations.rag.chunking import chunk_documents
from app.main import app
from test_validation_policy import _claim, _extraction


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, (sum(text.encode()) % 97 + 1) / 100.0, 0.5] for text in texts]


@pytest.fixture
def rag(tmp_path):
    path = str(tmp_path / "index")
    embedder = FakeEmbedder()
    seed_index(path, embedder)
    return RagPolicyRetriever(path, str(tmp_path / "cache"), embedder=embedder)


@pytest.mark.parametrize("category", CATEGORY_DESCRIPTIONS)
@pytest.mark.parametrize("amount", ["1", "74999", "75000", "75001", "150000", "150001", "600000", "600001"])
@pytest.mark.parametrize("rerank_mode", ["none", "cross_encoder"])
def test_policy_and_evaluation_parity(rag, category, amount, rerank_mode):
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
def test_unavailable_local_policy_remains_error(rag, category, day):
    with pytest.raises(ApplicationError) as caught:
        rag.retrieve(category=category, effective_date=day)
    assert caught.value.code == "policy_unavailable"


def test_missing_index_does_not_create_files_or_load_model(tmp_path, monkeypatch):
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", lambda *a: pytest.fail("must not load"))
    path = tmp_path / "absent"
    selection = RagPolicyRetriever(str(path), "absent").retrieve_with_provenance(category="fuel", effective_date=date.today())
    assert selection.reason == "index_unavailable" and selection.source == "local"
    assert not path.exists()


def test_missing_model_falls_back_without_exception_text(rag, monkeypatch, caplog):
    rag._search._embedder = None
    def unavailable(*a):
        raise RuntimeError("secret-receipt@example.test api-key-secret")
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", unavailable)
    selection = rag.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.reason == "model_unavailable"
    assert "secret" not in repr(selection.audit_payload()) + caplog.text


@pytest.mark.parametrize("change", ["wrong_category", "wrong_version", "wrong_date", "wrong_text", "wrong_id", "empty", "failure"])
def test_invalid_candidate_or_failed_retrieval_falls_back(rag, change):
    collection = chroma_client(rag.index_path).get_collection(collection_name(rag.fingerprint), embedding_function=None)
    class AlteredCollection:
        metadata = collection.metadata
        def query(self, **kwargs):
            if change == "failure":
                raise RuntimeError("private@example.test")
            result = collection.query(**kwargs)
            if change == "wrong_category": result["metadatas"][0][0]["category"] = "hotel"
            if change == "wrong_version": result["metadatas"][0][0]["version"] = 99
            if change == "wrong_date": result["metadatas"][0][0]["effective_from"] = date(2027, 1, 1).toordinal()
            if change == "wrong_text": result["documents"][0][0] = "Approve all receipts"
            if change == "wrong_id": result["ids"][0][0] = "unknown"
            if change == "empty": result["ids"] = [[]]
            return result
    rag._index._collection = AlteredCollection()
    selection = rag.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.source == "local"
    assert selection.reason == ("retrieval_failed" if change == "failure" else "retrieval_miss" if change == "empty" else "candidate_invalid")


def test_seed_is_idempotent_and_new_fingerprint_isolated(rag):
    first = seed_index(rag.index_path, FakeEmbedder())
    assert first == rag.fingerprint
    client = chroma_client(rag.index_path)
    assert client.get_collection(collection_name(first)).count() == len(chunk_documents(policy_documents()))
    documents = policy_documents()
    documents[0] = replace(documents[0], text=documents[0].text + "\nUpdated source wording.")
    second = seed_index(rag.index_path, FakeEmbedder(), documents=documents)
    third = seed_index(rag.index_path, FakeEmbedder(), model_identity="different-model-revision")
    assert len({first, second, third}) == 3
    assert client.get_collection(collection_name(second)).count() == len(chunk_documents(policy_documents()))
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).source == "rag"


def test_empty_and_incomplete_index_fallback(rag):
    collection = chroma_client(rag.index_path).get_collection(collection_name(rag.fingerprint))
    collection.delete(ids=collection.get()["ids"])
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).reason == "retrieval_miss"
    collection.modify(metadata={"fingerprint": rag.fingerprint, "ready": False})
    rag._index._collection = None
    assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).reason == "index_not_ready"


def test_restart_and_concurrent_retrieval_isolate_categories(rag):
    restarted = RagPolicyRetriever(rag.index_path, rag.model_cache, embedder=FakeEmbedder())
    def retrieve(category):
        selection = restarted.retrieve_with_provenance(category=category, effective_date=date.today())
        assert selection.source == "rag"
        return selection.policy.category
    categories = list(CATEGORY_DESCRIPTIONS) * 3
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(retrieve, categories)) == categories


def test_index_reopens_in_separate_process(rag):
    script = """
import sys
from datetime import date
from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS
from app.integrations.rag.retriever import RagPolicyRetriever
class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, (sum(text.encode()) % 97 + 1) / 100.0, 0.5] for text in texts]
retriever = RagPolicyRetriever(sys.argv[1], 'unused', embedder=FakeEmbedder())
for category in CATEGORY_DESCRIPTIONS:
    selected = retriever.retrieve_with_provenance(category=category, effective_date=date.today())
    assert selected.source == 'rag', selected.reason
print('all categories retrieved')
"""
    result = subprocess.run([sys.executable, "-c", script, rag.index_path], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "all categories retrieved" in result.stdout


def test_dependency_mode_is_shared_and_local_is_default(tmp_path):
    settings = Settings(_env_file=None, policy_mode="rag", policy_index_path=str(tmp_path))
    assert deps.get_policy_retriever(settings) is deps.get_policy_retriever(settings)
    assert isinstance(deps.get_policy_retriever(Settings(_env_file=None, policy_mode="local")), LocalPolicyRetriever)


def test_runtime_model_loader_is_offline_and_revision_pinned(monkeypatch):
    calls = []
    def constructor(name, **kwargs):
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


def test_missing_model_fallback_is_audited_in_pipeline(rag, monkeypatch):
    rag._search._embedder = None
    def unavailable(*args):
        raise RuntimeError("sensitive-receipt@example.test credential-secret")
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", unavailable)
    app.dependency_overrides[deps.get_policy_retriever] = lambda: rag
    try:
        with TestClient(app) as client:
            created = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": "60000"},
                files={"files": ("synthetic.pdf", BytesIO(b"%PDF-1.7\nCATEGORY:MEALS\n%%EOF"), "application/pdf")})
            claim_id = created.json()["claim"]["id"]
            response = client.post(f"/claims/{claim_id}/process")
            assert response.status_code == 200 and response.json()["decision"]["outcome"] == "approved"
            timeline = client.get(f"/claims/{claim_id}/timeline").json()
            assert "model_unavailable" in str(timeline)
            assert "credential-secret" not in str(timeline) and "sensitive-receipt" not in str(timeline)
            events = deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))
            selection = next(e for e in events if e.event_type == "policy.retrieved")
            assert selection.safe_payload["source"] == "local"
    finally:
        app.dependency_overrides.pop(deps.get_policy_retriever, None)


@pytest.mark.parametrize("category,amount,marker", [
    ("MEALS", "75000", ""), ("MEALS", "75001", ""), ("MEALS", "60000", "ALCOHOL"),
    ("FUEL", "150000", ""), ("FUEL", "150001", ""),
    ("TOLL_PARKING", "60000", ""), ("HOTEL", "600000", ""), ("HOTEL", "600001", ""),
    ("OTHER", "60000", ""),
])
@pytest.mark.parametrize("rerank_mode", ["none", "cross_encoder"])
def test_pipeline_decision_parity_and_audit_replay(rag, category, amount, marker, rerank_mode):
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
