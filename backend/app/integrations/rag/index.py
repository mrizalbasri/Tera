"""Explicit index ingestion and cached opening of immutable Chroma generations."""

from datetime import date
from pathlib import Path

from app.integrations.rag.chunking import PolicyChunk, chunk_documents
from app.integrations.rag.corpus import PolicyDocument, index_fingerprint, policy_documents
from app.integrations.rag.embeddings import MODEL_IDENTITY, Embedder
from app.integrations.rag.errors import RetrievalError


def chroma_client(path: str):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))


def collection_name(fingerprint: str) -> str:
    return f"policies-{fingerprint}"


def chunk_metadata(chunk: PolicyChunk, document: PolicyDocument, fingerprint: str) -> dict:
    policy = document.policy
    return {
        "document_id": document.id, "rule_id": chunk.rule_id,
        "category": policy.category, "effective_from": policy.effective_from.toordinal(),
        "effective_to": policy.effective_to.toordinal() if policy.effective_to else date.max.toordinal(),
        "policy_id": policy.policy_id, "version": policy.version,
        "source": document.source, "fingerprint": fingerprint,
    }


def seed_index(
    path: str, embedder: Embedder, *, documents: list[PolicyDocument] | None = None,
    model_identity: str = MODEL_IDENTITY,
) -> str:
    """Run with the API stopped; interrupted seeds leave a non-ready generation."""
    documents = documents if documents is not None else policy_documents()
    chunks = chunk_documents(documents)
    known = {document.id: document for document in documents}
    fingerprint = index_fingerprint(documents, model_identity)
    collection = chroma_client(path).get_or_create_collection(
        name=collection_name(fingerprint), embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"fingerprint": fingerprint, "model": model_identity, "ready": False},
    )
    collection.modify(metadata={"fingerprint": fingerprint, "model": model_identity, "ready": False})
    if chunks:
        collection.upsert(
            ids=[chunk.id for chunk in chunks], documents=[chunk.text for chunk in chunks],
            embeddings=embedder.embed([chunk.text for chunk in chunks]),
            metadatas=[chunk_metadata(chunk, known[chunk.document_id], fingerprint) for chunk in chunks],
        )
    collection.modify(metadata={"fingerprint": fingerprint, "model": model_identity, "ready": True})
    return fingerprint


class PolicyIndex:
    def __init__(self, path: str, documents: list[PolicyDocument], model_identity: str) -> None:
        self.path = path
        self.model_identity = model_identity
        self.fingerprint = index_fingerprint(documents, model_identity)
        self.documents = {document.id: document for document in documents}
        self.chunks = {chunk.id: chunk for chunk in chunk_documents(documents)}
        self._collection = None

    def open(self):
        if not (Path(self.path) / "chroma.sqlite3").is_file():
            raise RetrievalError("index_unavailable")
        if self._collection is None:
            try:
                self._collection = chroma_client(self.path).get_collection(
                    collection_name(self.fingerprint), embedding_function=None,
                )
            except Exception:
                raise RetrievalError("index_unavailable") from None
        metadata = self._collection.metadata or {}
        if metadata != {"fingerprint": self.fingerprint, "model": self.model_identity, "ready": True}:
            raise RetrievalError("index_not_ready")
        return self._collection
