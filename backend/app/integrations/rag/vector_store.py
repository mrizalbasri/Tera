"""Storage contract for policy generations and vector search."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class Generation:
    fingerprint: str
    model: str
    dimensions: int
    ready: bool
    record_count: int


@dataclass(frozen=True)
class VectorRecord:
    chunk_id: str
    text: str
    metadata: dict
    embedding: list[float]


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    text: str
    metadata: dict
    distance: float


class PolicyVectorStore(Protocol):
    def seed(self, generation: Generation, records: list[VectorRecord]) -> None: ...

    def generation(self, fingerprint: str) -> Generation | None: ...

    def count(self, fingerprint: str) -> int: ...

    def search(self, fingerprint: str, embedding: list[float], *, category: str,
               effective_date: date, top_k: int) -> list[SearchHit]: ...

    def close(self) -> None: ...
