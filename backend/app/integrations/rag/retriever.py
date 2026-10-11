"""Policy retrieval orchestration; selection never changes deterministic rules."""

from dataclasses import dataclass
from datetime import date
from threading import RLock
from typing import Literal

from app.errors import ApplicationError, ErrorCode
from app.integrations.policy_local import LocalPolicyRetriever
from app.integrations.rag.corpus import PolicyDocument, policy_documents
from app.integrations.rag.embeddings import MODEL_IDENTITY, Embedder
from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.index import PolicyIndex
from app.integrations.rag.query import PolicyQueryContext, build_query
from app.integrations.rag.reranker import (
    RERANK_MODEL_IDENTITY, CrossEncoderReranker, Reranker, rerank_candidates,
)
from app.integrations.rag.search import PolicySearch
from app.integrations.rag.vector_store import PolicyVectorStore
from app.schemas.core import Policy


@dataclass(frozen=True)
class PolicySelection:
    policy: Policy
    source: str
    fingerprint: str
    reason: str
    chunk_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    candidate_count: int = 0
    embedding_model: str = MODEL_IDENTITY
    reranker_model: str | None = None

    def require_policy(self) -> Policy:
        """Only successful retrieval or a genuine miss may reach evaluation."""
        if self.reason not in {"retrieved", "retrieval_miss"}:
            raise ApplicationError(
                ErrorCode.POLICY_UNAVAILABLE,
                "Policy retrieval failed; the claim cannot be approved automatically.",
                503,
            )
        return self.policy

    def audit_payload(self) -> dict[str, object]:
        return {
            "source": self.source, "policy_id": self.policy.policy_id,
            "policy_version": self.policy.version, "index_fingerprint": self.fingerprint,
            "reason_code": self.reason, "chunk_ids": list(self.chunk_ids),
            "rule_ids": list(self.rule_ids), "candidate_count": self.candidate_count,
            "embedding_model": self.embedding_model, "reranker_model": self.reranker_model,
        }


class RagPolicyRetriever:
    def __init__(
        self, database_url: str, model_cache: str, *, embedder: Embedder | None = None,
        documents: list[PolicyDocument] | None = None, model_identity: str = MODEL_IDENTITY,
        top_k: int = 8, top_n: int = 3, rerank_mode: Literal["none", "cross_encoder"] = "none",
        reranker_cache: str = "./data/local/policy_reranker", reranker: Reranker | None = None,
        index_schema: str = "rag", store: PolicyVectorStore | None = None,
    ) -> None:
        if not (1 <= top_n <= top_k <= 50) or rerank_mode not in ("none", "cross_encoder"):
            raise ValueError("invalid_retrieval_configuration")
        documents = documents if documents is not None else policy_documents()
        self.model_cache = model_cache
        self._index = PolicyIndex(database_url, documents, model_identity, schema=index_schema, store=store)
        self.fingerprint = self._index.fingerprint
        self._search = PolicySearch(self._index, model_cache, embedder)
        self.top_k, self.top_n = top_k, top_n
        self.rerank_mode, self.reranker_cache = rerank_mode, reranker_cache
        self._reranker = reranker
        self._lock = RLock()
        self._local = LocalPolicyRetriever()

    def retrieve(self, *, category: str, effective_date: date) -> Policy:
        return self.retrieve_with_provenance(category=category, effective_date=effective_date).require_policy()

    def retrieve_with_provenance(
        self, *, category: str, effective_date: date, context: PolicyQueryContext | None = None,
    ) -> PolicySelection:
        local = self._local.retrieve(category=category, effective_date=effective_date)
        with self._lock:
            stage = "retrieval_failed"
            try:
                query = build_query(category, context)
                candidates = self._search.search(query, category=category, effective_date=effective_date, top_k=self.top_k)
                # All candidates must resolve to the current complete local record.
                if any(self._index.documents[c.document_id].policy != local for c in candidates):
                    raise RetrievalError("candidate_invalid")
                if self.rerank_mode == "cross_encoder":
                    stage = "reranker_unavailable"
                    if self._reranker is None:
                        self._reranker = CrossEncoderReranker(self.reranker_cache)
                    stage = "rerank_failed"
                    selected = rerank_candidates(query, candidates, self._reranker, self.top_n)
                else:
                    selected = candidates[:self.top_n]
                return PolicySelection(
                    policy=local.model_copy(deep=True), source="rag", fingerprint=self.fingerprint,
                    reason="retrieved", chunk_ids=tuple(c.chunk_id for c in selected),
                    rule_ids=tuple(c.rule_id for c in selected), candidate_count=len(candidates),
                    embedding_model=self._index.model_identity,
                    reranker_model=RERANK_MODEL_IDENTITY if self.rerank_mode == "cross_encoder" else None,
                )
            except RetrievalError as exc:
                reason = exc.code
            except Exception:
                reason = stage
            # No query, receipt text or exception message crosses this boundary.
            return PolicySelection(
                local, "local", self.fingerprint, reason,
                embedding_model=self._index.model_identity,
                reranker_model=RERANK_MODEL_IDENTITY if self.rerank_mode == "cross_encoder" else None,
            )
