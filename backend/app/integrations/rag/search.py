"""Filtered cosine retrieval with a strict trusted-corpus boundary."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

from app.integrations.rag.embeddings import Embedder, SentenceEmbedder
from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.index import PolicyIndex, chunk_metadata
from app.integrations.rag.pgvector import vector_literal


@dataclass(frozen=True)
class Candidate:
    chunk_id: str
    document_id: str
    rule_id: str
    text: str
    distance: float


class PolicySearch:
    def __init__(self, index: PolicyIndex, model_cache: str, embedder: Embedder | None = None) -> None:
        self.index = index
        self.model_cache = model_cache
        self._embedder = embedder

    def search(self, query: str, *, category: str, effective_date: date, top_k: int) -> list[Candidate]:
        generation = self.index.open()
        if self._embedder is None:
            try:
                self._embedder = SentenceEmbedder(self.model_cache)
            except Exception:
                raise RetrievalError("model_unavailable") from None
        embeddings = self._embedder.embed([query])
        if len(embeddings) != 1:
            raise RetrievalError("retrieval_failed")
        vector_literal(embeddings[0], generation.dimensions)
        hits = self.index.store.search(self.index.fingerprint, embeddings[0], category=category,
                                       effective_date=effective_date, top_k=top_k)
        if not hits:
            raise RetrievalError("retrieval_miss")
        candidates = []
        try:
            if len(hits) > top_k or len({hit.chunk_id for hit in hits}) != len(hits):
                raise ValueError
            for hit in hits:
                chunk = self.index.chunks[hit.chunk_id]
                document = self.index.documents[chunk.document_id]
                policy = document.policy
                if (hit.metadata != chunk_metadata(chunk, document, self.index.fingerprint)
                    or hit.text != chunk.text or policy.category != category
                    or effective_date < policy.effective_from
                    or (policy.effective_to is not None and effective_date > policy.effective_to)
                    or isinstance(hit.distance, bool) or not isfinite(float(hit.distance))):
                    raise ValueError
                candidates.append(Candidate(hit.chunk_id, document.id, chunk.rule_id, chunk.text, float(hit.distance)))
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise RetrievalError("candidate_invalid") from None
        # Explicit tie breaking keeps fake embeddings and identical distances reproducible.
        return sorted(candidates, key=lambda candidate: (candidate.distance, candidate.chunk_id))
