"""Local semantic selection of trusted policies; never interprets retrieved rules."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from threading import RLock
from typing import Protocol

from app.integrations.rag.corpus import (
    CATEGORY_DESCRIPTIONS, PolicyDocument, index_fingerprint, policy_documents,
)
from app.integrations.policy_local import LocalPolicyRetriever
from app.schemas.core import Policy


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MODEL_IDENTITY = f"{MODEL_NAME}@{MODEL_REVISION}:normalized-cpu-v1"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceEmbedder:
    def __init__(self, cache_path: str, *, download: bool = False) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            MODEL_NAME, revision=MODEL_REVISION, cache_folder=cache_path,
            local_files_only=not download, device="cpu", trust_remote_code=False,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def chroma_client(path: str):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))


def collection_name(fingerprint: str) -> str:
    return f"policies-{fingerprint}"


def seed_index(
    path: str, embedder: Embedder, *, documents: list[PolicyDocument] | None = None,
    model_identity: str = MODEL_IDENTITY,
) -> str:
    """Explicit seed only. Each immutable corpus/model generation has its own index."""
    documents = documents if documents is not None else policy_documents()
    fingerprint = index_fingerprint(documents, model_identity)
    client = chroma_client(path)
    collection = client.get_or_create_collection(
        name=collection_name(fingerprint), embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"fingerprint": fingerprint, "model": model_identity, "ready": False},
    )
    collection.modify(metadata={"fingerprint": fingerprint, "model": model_identity, "ready": False})
    if documents:
        collection.upsert(
            ids=[d.id for d in documents], documents=[d.text for d in documents],
            embeddings=embedder.embed([d.text for d in documents]),
            metadatas=[{
                "category": d.policy.category, "effective_from": d.policy.effective_from.toordinal(),
                "effective_to": d.policy.effective_to.toordinal() if d.policy.effective_to else date.max.toordinal(),
                "policy_id": d.policy.policy_id, "version": d.policy.version,
                "source": d.source, "fingerprint": fingerprint,
            } for d in documents],
        )
    collection.modify(metadata={"fingerprint": fingerprint, "model": model_identity, "ready": True})
    return fingerprint


@dataclass(frozen=True)
class PolicySelection:
    policy: Policy
    source: str
    fingerprint: str
    reason: str

    def audit_payload(self) -> dict:
        return {"source": self.source, "policy_id": self.policy.policy_id,
                "policy_version": self.policy.version, "index_fingerprint": self.fingerprint,
                "reason_code": self.reason}


class RagPolicyRetriever:
    def __init__(
        self, index_path: str, model_cache: str, *, embedder: Embedder | None = None,
        documents: list[PolicyDocument] | None = None, model_identity: str = MODEL_IDENTITY,
    ) -> None:
        self.index_path = index_path
        self.model_cache = model_cache
        self._embedder = embedder
        self._documents = documents if documents is not None else policy_documents()
        self.fingerprint = index_fingerprint(self._documents, model_identity)
        self._known = {d.id: d for d in self._documents}
        self._model_identity = model_identity
        self._collection = None
        self._lock = RLock()
        self._local = LocalPolicyRetriever()

    def retrieve(self, *, category: str, effective_date: date) -> Policy:
        return self.retrieve_with_provenance(category=category, effective_date=effective_date).policy

    def retrieve_with_provenance(self, *, category: str, effective_date: date) -> PolicySelection:
        # Local availability remains authoritative for the seeded policy set.
        local = self._local.retrieve(category=category, effective_date=effective_date)
        reason = "index_unavailable"
        with self._lock:
            try:
                if not (Path(self.index_path) / "chroma.sqlite3").is_file():
                    return PolicySelection(local, "local", self.fingerprint, reason)
                if self._collection is None:
                    self._collection = chroma_client(self.index_path).get_collection(
                        collection_name(self.fingerprint), embedding_function=None,
                    )
                metadata = self._collection.metadata or {}
                if metadata != {"fingerprint": self.fingerprint, "model": self._model_identity, "ready": True}:
                    return PolicySelection(local, "local", self.fingerprint, "index_not_ready")
                reason = "model_unavailable"
                if self._embedder is None:
                    self._embedder = SentenceEmbedder(self.model_cache)
                reason = "retrieval_failed"
                result = self._collection.query(
                    query_embeddings=self._embedder.embed([f"{category}: {CATEGORY_DESCRIPTIONS[category]}"]),
                    n_results=1, where={"$and": [
                        {"category": category}, {"effective_from": {"$lte": effective_date.toordinal()}},
                        {"effective_to": {"$gte": effective_date.toordinal()}},
                    ]}, include=["metadatas", "documents"],
                )
                ids = result["ids"][0]
                if not ids:
                    return PolicySelection(local, "local", self.fingerprint, "retrieval_miss")
                document = self._known.get(ids[0])
                candidate = result["metadatas"][0][0]
                if (document is None or document.policy != local or
                    candidate.get("category") != category or
                    candidate.get("policy_id") != local.policy_id or
                    candidate.get("version") != local.version or
                    candidate.get("fingerprint") != self.fingerprint or
                    candidate.get("source") != document.source or
                    candidate.get("effective_from") != local.effective_from.toordinal() or
                    candidate.get("effective_to") != (local.effective_to.toordinal() if local.effective_to else date.max.toordinal()) or
                    result["documents"][0][0] != document.text):
                    return PolicySelection(local, "local", self.fingerprint, "candidate_invalid")
                return PolicySelection(document.policy.model_copy(deep=True), "rag", self.fingerprint, "retrieved")
            except Exception:
                # Never record provider/library exception text: it may contain secrets.
                return PolicySelection(local, "local", self.fingerprint, reason)
