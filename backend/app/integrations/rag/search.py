"""Filtered cosine retrieval with a strict trusted-corpus boundary."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

from app.integrations.rag.embeddings import Embedder, SentenceEmbedder
from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.index import PolicyIndex, chunk_metadata


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
        collection = self.index.open()
        if self._embedder is None:
            try:
                self._embedder = SentenceEmbedder(self.model_cache)
            except Exception:
                raise RetrievalError("model_unavailable") from None
        result = collection.query(
            query_embeddings=self._embedder.embed([query]), n_results=top_k,
            where={"$and": [
                {"category": category}, {"effective_from": {"$lte": effective_date.toordinal()}},
                {"effective_to": {"$gte": effective_date.toordinal()}},
            ]}, include=["metadatas", "documents", "distances"],
        )
        ids = result["ids"][0]
        if not ids:
            raise RetrievalError("retrieval_miss")
        candidates = []
        try:
            metadatas, texts, distances = (result[key][0] for key in ("metadatas", "documents", "distances"))
            if len(ids) > top_k or len(set(ids)) != len(ids) or not (len(ids) == len(metadatas) == len(texts) == len(distances)):
                raise ValueError
            for chunk_id, metadata, text, distance in zip(ids, metadatas, texts, distances, strict=True):
                chunk = self.index.chunks[chunk_id]
                document = self.index.documents[chunk.document_id]
                policy = document.policy
                if (metadata != chunk_metadata(chunk, document, self.index.fingerprint)
                    or text != chunk.text or policy.category != category
                    or effective_date < policy.effective_from
                    or (policy.effective_to is not None and effective_date > policy.effective_to)
                    or isinstance(distance, bool) or not isfinite(float(distance))):
                    raise ValueError
                candidates.append(Candidate(chunk_id, document.id, chunk.rule_id, chunk.text, float(distance)))
        except (KeyError, IndexError, TypeError, ValueError):
            raise RetrievalError("candidate_invalid") from None
        # Explicit tie breaking keeps fake embeddings and identical distances reproducible.
        return sorted(candidates, key=lambda candidate: (candidate.distance, candidate.chunk_id))
