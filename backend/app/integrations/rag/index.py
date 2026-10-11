"""Trusted corpus boundary and explicit pgvector ingestion."""

from datetime import date

from app.integrations.rag.chunking import PolicyChunk, chunk_documents
from app.integrations.rag.corpus import PolicyDocument, index_fingerprint, policy_documents
from app.integrations.rag.embeddings import MODEL_IDENTITY, Embedder
from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.pgvector import PgPolicyStore, vector_literal
from app.integrations.rag.vector_store import Generation, PolicyVectorStore, VectorRecord


def chunk_metadata(
    chunk: PolicyChunk, document: PolicyDocument, fingerprint: str,
) -> dict[str, str | int]:
    policy = document.policy
    return {
        "document_id": document.id, "rule_id": chunk.rule_id,
        "category": policy.category, "effective_from": policy.effective_from.toordinal(),
        "effective_to": policy.effective_to.toordinal() if policy.effective_to else date.max.toordinal(),
        "policy_id": policy.policy_id, "version": policy.version,
        "source": document.source, "fingerprint": fingerprint,
    }


def seed_index(
    database_url: str, embedder: Embedder, *, schema: str = "rag",
    documents: list[PolicyDocument] | None = None, model_identity: str = MODEL_IDENTITY,
    store: PolicyVectorStore | None = None,
) -> str:
    """Explicit admin operation. Failed seeds preserve the last committed generation."""
    documents = documents if documents is not None else policy_documents()
    chunks = chunk_documents(documents)
    known = {document.id: document for document in documents}
    fingerprint = index_fingerprint(documents, model_identity)
    embeddings = embedder.embed([chunk.text for chunk in chunks]) if chunks else []
    if len(embeddings) != len(chunks):
        raise ValueError("invalid_embedding_count")
    dimensions = len(embeddings[0]) if embeddings else 384
    for embedding in embeddings:
        vector_literal(embedding, dimensions)
    adapter = store if store is not None else PgPolicyStore(database_url, schema)
    try:
        adapter.seed(Generation(fingerprint, model_identity, dimensions, True), [
            VectorRecord(chunk.id, chunk.text, chunk_metadata(chunk, known[chunk.document_id], fingerprint), embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ])
    finally:
        if store is None:
            adapter.close()
    return fingerprint


class PolicyIndex:
    def __init__(self, database_url: str, documents: list[PolicyDocument], model_identity: str,
                 *, schema: str = "rag", store: PolicyVectorStore | None = None) -> None:
        self.model_identity = model_identity
        self.fingerprint = index_fingerprint(documents, model_identity)
        self.documents = {document.id: document for document in documents}
        self.chunks = {chunk.id: chunk for chunk in chunk_documents(documents)}
        self.store = store if store is not None else PgPolicyStore(database_url, schema)

    def open(self) -> Generation:
        try:
            generation = self.store.generation(self.fingerprint)
        except Exception:
            raise RetrievalError("index_unavailable") from None
        if generation is None:
            raise RetrievalError("index_unavailable")
        if (generation.fingerprint != self.fingerprint or generation.model != self.model_identity
            or not generation.ready or generation.dimensions < 1 or generation.dimensions > 16000):
            raise RetrievalError("index_not_ready")
        return generation
