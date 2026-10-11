"""Storage/model fakes for offline retrieval unit tests; no dotenv or networking."""

from copy import deepcopy
from datetime import date
from math import sqrt

from app.integrations.rag.vector_store import Generation, SearchHit, VectorRecord


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, (sum(text.encode()) % 97 + 1) / 100.0, 0.5] for text in texts]


class MemoryVectorStore:
    def __init__(self) -> None:
        self.generations: dict[str, Generation] = {}
        self.records: dict[str, list[VectorRecord]] = {}

    def seed(self, generation: Generation, records: list[VectorRecord]) -> None:
        self.generations[generation.fingerprint] = generation
        self.records[generation.fingerprint] = deepcopy(records)

    def generation(self, fingerprint: str) -> Generation | None:
        return self.generations.get(fingerprint)

    def search(
        self, fingerprint: str, embedding: list[float], *, category: str,
        effective_date: date, top_k: int,
    ) -> list[SearchHit]:
        day = effective_date.toordinal()
        hits: list[SearchHit] = []
        for record in self.records.get(fingerprint, []):
            meta = record.metadata
            if meta['category'] != category or not meta['effective_from'] <= day <= meta['effective_to']:
                continue
            similarity = sum(a*b for a, b in zip(embedding, record.embedding, strict=True)) / (
                sqrt(sum(a*a for a in embedding)) * sqrt(sum(b*b for b in record.embedding)))
            hits.append(SearchHit(record.chunk_id, record.text, deepcopy(meta), 1-similarity))
        return sorted(hits, key=lambda hit: (hit.distance, hit.chunk_id))[:top_k]

    def close(self) -> None:
        pass
