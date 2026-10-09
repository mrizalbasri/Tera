"""Storage/model fakes for offline retrieval unit tests; no dotenv or networking."""

from copy import deepcopy
from math import sqrt

from app.integrations.rag.vector_store import SearchHit


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, (sum(text.encode()) % 97 + 1) / 100.0, 0.5] for text in texts]


class MemoryVectorStore:
    def __init__(self):
        self.generations = {}
        self.records = {}

    def seed(self, generation, records):
        self.generations[generation.fingerprint] = generation
        self.records[generation.fingerprint] = deepcopy(records)

    def generation(self, fingerprint):
        return self.generations.get(fingerprint)

    def search(self, fingerprint, embedding, *, category, effective_date, top_k):
        day = effective_date.toordinal()
        hits = []
        for record in self.records.get(fingerprint, []):
            meta = record.metadata
            if meta['category'] != category or not meta['effective_from'] <= day <= meta['effective_to']:
                continue
            similarity = sum(a*b for a, b in zip(embedding, record.embedding, strict=True)) / (
                sqrt(sum(a*a for a in embedding)) * sqrt(sum(b*b for b in record.embedding)))
            hits.append(SearchHit(record.chunk_id, record.text, deepcopy(meta), 1-similarity))
        return sorted(hits, key=lambda hit: (hit.distance, hit.chunk_id))[:top_k]

    def close(self):
        pass
