"""Modular retrieval behavior using real temporary Chroma and fake local models."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4
import json
import sys

from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.config import Settings
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.rag.chunking import chunk_documents
from app.integrations.rag.corpus import index_fingerprint, policy_documents
from app.integrations.rag.embeddings import MODEL_IDENTITY
from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.index import chroma_client, collection_name, seed_index
from app.integrations.rag.query import PolicyQueryContext, build_query
from app.integrations.rag.reranker import (
    RERANK_MODEL_NAME, RERANK_MODEL_REVISION, CrossEncoderReranker, rerank_candidates,
)
from app.integrations.rag.retriever import RagPolicyRetriever
from app.integrations.rag.search import Candidate
from app.main import app
from app.schemas.core import ExtractedLineItem
from test_policy_rag import FakeEmbedder
from test_validation_policy import _claim, _extraction


class FakeReranker:
    def __init__(self):
        self.calls = []

    def score(self, query, texts):
        self.calls.append((query, texts))
        return [float('"rule_id":"prohibited_items"' in text) for text in texts]


@pytest.fixture
def reranked(tmp_path):
    path = str(tmp_path / "index")
    seed_index(path, FakeEmbedder())
    return RagPolicyRetriever(path, str(tmp_path / "embedding"), embedder=FakeEmbedder(),
                              rerank_mode="cross_encoder", reranker=FakeReranker(), top_n=1)


def test_atomic_chunks_contain_all_rule_fields_and_stable_provenance():
    documents = policy_documents()
    chunks = chunk_documents(documents)
    assert chunks == chunk_documents(documents)
    assert len(chunks) == 15 and len({chunk.id for chunk in chunks}) == 15
    for document in documents:
        selected = [chunk for chunk in chunks if chunk.document_id == document.id]
        assert len(selected) == max(1, len(document.policy.rules))
        for rule in document.policy.rules:
            chunk = next(chunk for chunk in selected if chunk.rule_id == rule.rule_id)
            assert json.loads(chunk.text.splitlines()[-1]) == rule.model_dump(mode="json")
            assert document.source in chunk.text and document.policy.category in chunk.text


def test_chunk_fingerprint_changes_when_rules_or_source_change():
    documents = policy_documents()
    original = index_fingerprint(documents, MODEL_IDENTITY)
    changed = documents[0].policy.model_copy(deep=True)
    changed.rules[0].limit += 1
    assert index_fingerprint([replace(documents[0], policy=changed), *documents[1:]], MODEL_IDENTITY) != original
    assert index_fingerprint([replace(documents[0], source="synthetic-policy#9"), *documents[1:]], MODEL_IDENTITY) != original


def test_duplicate_rules_cannot_seed_ambiguous_chunk_ids():
    document = policy_documents()[0]
    policy = document.policy.model_copy(deep=True)
    policy.rules.append(policy.rules[0])
    with pytest.raises(ValueError, match="duplicate_policy_chunk_id"):
        chunk_documents([replace(document, policy=policy)])


def test_context_is_bounded_canonical_and_contains_no_free_text():
    extraction = _extraction()
    extraction.vendor.value = "SPBU Jane Doe private@example.test rekening 1234567890"
    extraction.line_items = [ExtractedLineItem(
        description="Beer untuk Jane Doe credential-secret 4111111111111111",
        quantity=1, unit_price=100, total=100,
    )]
    context = PolicyQueryContext.from_extraction(extraction, participants=999999)
    query = build_query("meals", context)
    assert context.participants == 1000
    assert "alkohol" in query and "nota SPBU" in query
    for forbidden in ("Jane", "Doe", "private", "@", "rekening", "1234567890", "credential", "4111111111111111"):
        assert forbidden not in query
    forged = PolicyQueryContext(("private@example.test", "alkohol", "credential-secret"), -1)
    assert "private" not in build_query("meals", forged)
    assert "jumlah peserta 1" in build_query("meals", forged)
    assert build_query("meals", PolicyQueryContext(("private@example.test",))) == build_query("meals")


def test_unrecognized_context_uses_fixed_category_query():
    extraction = _extraction()
    extraction.vendor.value = "Jane Doe"
    extraction.line_items = []
    assert build_query("meals", PolicyQueryContext.from_extraction(extraction)) == build_query("meals")


def test_search_filters_top_k_and_reranks_contextual_candidates(reranked):
    collection = reranked._index.open()
    captured = []
    class RecordingCollection:
        metadata = collection.metadata
        def query(self, **kwargs):
            captured.append(kwargs)
            return collection.query(**kwargs)
    reranked._index._collection = RecordingCollection()
    selection = reranked.retrieve_with_provenance(
        category="meals", effective_date=date(2026, 1, 1), context=PolicyQueryContext(("alkohol",)),
    )
    assert selection.source == "rag" and selection.rule_ids == ("prohibited_items",)
    assert selection.candidate_count == 3 and len(selection.chunk_ids) == 1
    assert captured[0]["n_results"] == 8
    assert captured[0]["where"]["$and"] == [
        {"category": "meals"}, {"effective_from": {"$lte": date(2026, 1, 1).toordinal()}},
        {"effective_to": {"$gte": date(2026, 1, 1).toordinal()}},
    ]
    assert len(reranked._reranker.calls[0][1]) == 3
    assert "alkohol" in reranked._reranker.calls[0][0]


def test_top_n_one_still_evaluates_every_rule(reranked):
    selection = reranked.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert len(selection.rule_ids) == 1
    assert selection.policy == LocalPolicyRetriever().retrieve(category="meals", effective_date=date.today())
    evaluations = LocalPolicyEvaluator().evaluate(claim=_claim("75001"), extraction=_extraction(total="75001"),
                                                policy=selection.policy, processing_run_id=uuid4())
    assert {evaluation.rule_id for evaluation in evaluations} == {rule.rule_id for rule in selection.policy.rules}
    assert next(e for e in evaluations if e.rule_id == "meal_daily_limit").passed is False


@pytest.mark.parametrize("scores", [[float("nan")], [float("inf")], [float("-inf")], [], [0, 1], [None], [True]])
def test_invalid_rerank_scores_are_rejected(scores):
    candidate = Candidate("chunk", "policy", "rule", "trusted text", 0.1)
    with pytest.raises(RetrievalError, match="rerank_invalid"):
        rerank_candidates("synthetic", [candidate], SimpleNamespace(score=lambda *args: scores), 1)


def test_reranker_has_stable_tie_breaking_and_top_n():
    candidates = [Candidate(str(i), "policy", str(i), "trusted text", 0.1) for i in (3, 2, 1)]
    scorer = SimpleNamespace(score=lambda *args: [0.1, 0.1, 0.1])
    assert [c.chunk_id for c in rerank_candidates("synthetic", candidates, scorer, 2)] == ["1", "2"]


@pytest.mark.parametrize("failure", ["missing", "exception", "invalid"])
def test_rerank_failure_uses_local_policy_and_safe_audit(reranked, monkeypatch, caplog, failure):
    secret = "private@example.test credential-secret"
    def fail(*args):
        raise RuntimeError(secret)
    if failure == "missing":
        reranked._reranker = None
        monkeypatch.setattr("app.integrations.rag.retriever.CrossEncoderReranker", fail)
    elif failure == "exception":
        reranked._reranker = SimpleNamespace(score=fail)
    else:
        reranked._reranker = SimpleNamespace(score=lambda *args: [float("nan")] * 3)
    selection = reranked.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.source == "local"
    assert selection.reason == {"missing": "reranker_unavailable", "exception": "rerank_failed", "invalid": "rerank_invalid"}[failure]
    assert "private" not in str(selection.audit_payload()) + caplog.text
    assert "credential-secret" not in str(selection.audit_payload()) + caplog.text


def test_candidate_tampering_is_rejected_before_reranking(reranked):
    collection = reranked._index.open()
    class Tampered:
        metadata = collection.metadata
        def query(self, **kwargs):
            result = collection.query(**kwargs)
            result["metadatas"][0][-1]["rule_id"] = "forged"
            return result
    reranked._index._collection = Tampered()
    selection = reranked.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.reason == "candidate_invalid"
    assert reranked._reranker.calls == []


@pytest.mark.parametrize("change", ["duplicates", "nan", "missing_metadata", "different_policy", "wrong_parent"])
def test_malformed_search_results_cannot_enter_reranker(reranked, change):
    collection = reranked._index.open()
    class Tampered:
        metadata = collection.metadata
        def query(self, **kwargs):
            result = collection.query(**kwargs)
            if change == "duplicates":
                result["ids"][0][1] = result["ids"][0][0]
            elif change == "nan":
                result["distances"][0][0] = float("nan")
            elif change == "missing_metadata":
                result["metadatas"] = [[]]
            elif change == "wrong_parent":
                result["metadatas"][0][0]["document_id"] = "unknown"
            else:
                result["metadatas"][0][0]["version"] = 99
            return result
    reranked._index._collection = Tampered()
    selection = reranked.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.source == "local" and selection.reason == "candidate_invalid"
    assert reranked._reranker.calls == []


def test_no_rerank_mode_does_not_load_or_call_reranker(reranked, monkeypatch):
    reranked.rerank_mode = "none"
    def fail(*args):
        pytest.fail("reranker must stay unloaded")
    reranked._reranker.score = fail
    selection = reranked.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert selection.source == "rag" and selection.reranker_model is None


def test_reranker_is_offline_pinned_and_uses_safetensors(monkeypatch):
    calls = []
    def constructor(name, **kwargs):
        calls.append((name, kwargs))
        return object()
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=constructor))
    CrossEncoderReranker("synthetic-cache")
    CrossEncoderReranker("synthetic-cache", download=True)
    assert calls[0][0] == RERANK_MODEL_NAME
    assert calls[0][1]["revision"] == RERANK_MODEL_REVISION
    assert calls[0][1]["local_files_only"] is True and calls[1][1]["local_files_only"] is False
    assert calls[0][1]["trust_remote_code"] is False
    assert calls[0][1]["model_kwargs"]["use_safetensors"] is True


@pytest.mark.parametrize("settings", [dict(policy_top_k=0), dict(policy_top_n=0),
    dict(policy_top_k=51), dict(policy_top_k=1, policy_top_n=2), dict(policy_rerank_mode="external")])
def test_invalid_retrieval_settings_fail_at_startup(settings):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **settings)


def test_shared_adapter_cache_accounts_for_retrieval_configuration(tmp_path):
    base = Settings(_env_file=None, policy_mode="rag", policy_index_path=str(tmp_path))
    first = deps.get_policy_retriever(base)
    changed = base.model_copy(update={"policy_rerank_mode": "cross_encoder"})
    assert deps.get_policy_retriever(changed) is not first
    assert deps.get_policy_retriever(changed) is deps.get_policy_retriever(changed)


def test_reranked_queries_do_not_cross_claims_and_index_persists(reranked):
    contexts = [("meals", "alkohol"), ("fuel", "nota SPBU"), ("hotel", "perjalanan dinas")] * 3
    def retrieve(pair):
        category, concept = pair
        return reranked.retrieve_with_provenance(category=category, effective_date=date.today(),
                                                 context=PolicyQueryContext((concept,)))
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(retrieve, contexts))
    assert [r.policy.category for r in results] == [pair[0] for pair in contexts]
    assert all(r.source == "rag" for r in results)
    restarted = RagPolicyRetriever(reranked.index_path, "unused", embedder=FakeEmbedder(),
                                  rerank_mode="cross_encoder", reranker=FakeReranker())
    assert restarted.retrieve(category="meals", effective_date=date.today()) == results[0].policy


def test_pipeline_reranking_is_contextual_replay_safe_and_query_is_not_audited(reranked):
    app.dependency_overrides[deps.get_policy_retriever] = lambda: reranked
    try:
        with TestClient(app) as client:
            created = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": "60000"},
                files={"files": ("synthetic.pdf", BytesIO(b"%PDF-1.7\nCATEGORY:MEALS ALCOHOL\n%%EOF"), "application/pdf")})
            claim_id = created.json()["claim"]["id"]
            response = client.post(f"/claims/{claim_id}/process")
            assert response.status_code == 200, response.text
            assert response.json()["decision"]["outcome"] == "rejected"
            assert "alkohol" in reranked._reranker.calls[0][0]
            audit = deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))
            provenance = next(e.safe_payload for e in audit if e.event_type == "policy.retrieved")
            assert provenance["rule_ids"] == ["prohibited_items"]
            assert provenance["reranker_model"].startswith(RERANK_MODEL_NAME)
            assert "konteks:" not in json.dumps(provenance)
            assert response.json() == client.post(f"/claims/{claim_id}/process").json()
            assert len(reranked._reranker.calls) == 1
            assert len(deps._memory_repositories().audit.list_for_aggregate("claim", UUID(claim_id))) == len(audit)
    finally:
        app.dependency_overrides.pop(deps.get_policy_retriever, None)
    stored = chroma_client(reranked.index_path).get_collection(collection_name(reranked.fingerprint)).get(include=["documents"])
    assert all("konteks:" not in text for text in stored["documents"])


def test_explicit_seed_cli_prepares_reranker_and_verifies_offline(tmp_path, monkeypatch, capsys):
    import app.seed_policy as cli
    calls = []
    def fake_embedder(cache, *, download=False):
        calls.append(("embedding", download))
        return FakeEmbedder()
    def fake_reranker(cache, *, download=False):
        calls.append(("reranker", download))
        return FakeReranker()
    settings = Settings(_env_file=None, policy_index_path=str(tmp_path / "index"))
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "SentenceEmbedder", fake_embedder)
    monkeypatch.setattr(cli, "CrossEncoderReranker", fake_reranker)
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", fake_embedder)
    monkeypatch.setattr("app.integrations.rag.retriever.CrossEncoderReranker", fake_reranker)
    monkeypatch.setattr(sys, "argv", ["seed_policy", "--with-reranker", "--verify"])
    cli.main()
    assert ("reranker", True) in calls and ("reranker", False) in calls
    assert ("embedding", True) in calls and ("embedding", False) in calls
    assert "all 5 categories" in capsys.readouterr().out


def test_benchmark_measures_fixed_synthetic_queries_without_claims(reranked):
    from app.integrations.rag.benchmark import CASES, benchmark

    result = benchmark(reranked._search, reranked._reranker, top_k=8, top_n=3)
    assert result["cases"] == len(CASES)
    assert all(0 <= result[key] <= 1 for key in ("search_top1", "reranked_top1", "search_mrr_at_n", "reranked_mrr_at_n"))
    assert result["mean_search_ms"] >= 0 and result["mean_rerank_ms"] >= 0
    assert "query" not in json.dumps(result)
