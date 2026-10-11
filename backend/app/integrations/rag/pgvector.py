"""PostgreSQL policy-only vector storage with atomic explicit seeding."""

from datetime import date
import json
from math import isfinite
import re
from weakref import WeakSet

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.integrations.rag.vector_store import Generation, SearchHit, VectorRecord


_stores: WeakSet = WeakSet()


def validate_schema(schema: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema) or schema in ("public", "pg_catalog", "information_schema"):
        raise ValueError("invalid_policy_index_schema")
    return schema


def vector_literal(values: list[float], dimensions: int | None = None) -> str:
    if not values or (dimensions is not None and len(values) != dimensions):
        raise ValueError("invalid_embedding_dimensions")
    numbers = [float(value) for value in values]
    if any(isinstance(value, bool) for value in values) or not all(isfinite(number) and abs(number) <= 3.4e38 for number in numbers):
        raise ValueError("invalid_embedding_values")
    if not any(number != 0 for number in numbers):
        raise ValueError("zero_embedding")
    return "[" + ",".join(str(number) for number in numbers) + "]"


def close_policy_indexes() -> None:
    for store in list(_stores):
        store.close()


class PgPolicyStore:
    def __init__(self, database_url: str, schema: str = "rag") -> None:
        self._database_url = database_url
        self.schema = validate_schema(schema)
        self._pool: Engine | None = None
        _stores.add(self)

    def _engine(self) -> Engine:
        if self._pool is None:
            url = make_url(self._database_url)
            if url.get_backend_name() != "postgresql":
                raise ValueError("policy_index_requires_postgresql")
            url = url.set(drivername="postgresql+psycopg")
            self._pool = create_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True,
                                       hide_parameters=True, connect_args={"connect_timeout": 5})
        return self._pool

    def seed(self, generation: Generation, records: list[VectorRecord]) -> None:
        vectors = [vector_literal(record.embedding, generation.dimensions) for record in records]
        if generation.dimensions < 1 or generation.dimensions > 16000:
            raise ValueError("invalid_embedding_dimensions")
        schema = self.schema
        with self._engine().begin() as connection:
            # DDL is only permitted in this explicit admin operation, never API reads.
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            connection.execute(text(f'''
                CREATE TABLE IF NOT EXISTS "{schema}".policy_generations (
                    fingerprint TEXT PRIMARY KEY, model TEXT NOT NULL,
                    dimensions INTEGER NOT NULL CHECK (dimensions BETWEEN 1 AND 16000),
                    ready BOOLEAN NOT NULL, record_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            '''))
            connection.execute(text(
                f'ALTER TABLE "{schema}".policy_generations '
                'ADD COLUMN IF NOT EXISTS record_count INTEGER NOT NULL DEFAULT 0'
            ))
            connection.execute(text(f'''
                CREATE TABLE IF NOT EXISTS "{schema}".policy_chunks (
                    fingerprint TEXT NOT NULL REFERENCES "{schema}".policy_generations(fingerprint),
                    chunk_id TEXT NOT NULL, category TEXT NOT NULL,
                    effective_from INTEGER NOT NULL, effective_to INTEGER NOT NULL,
                    document TEXT NOT NULL, metadata JSONB NOT NULL,
                    embedding public.vector NOT NULL,
                    PRIMARY KEY (fingerprint, chunk_id),
                    CHECK (effective_from <= effective_to)
                )
            '''))
            connection.execute(text(f'CREATE INDEX IF NOT EXISTS policy_chunks_filter_idx '
                                    f'ON "{schema}".policy_chunks (fingerprint, category, effective_from)'))
            connection.execute(text(f'''
                INSERT INTO "{schema}".policy_generations (fingerprint, model, dimensions, ready)
                VALUES (:fingerprint, :model, :dimensions, false)
                ON CONFLICT (fingerprint) DO UPDATE
                SET model = EXCLUDED.model, dimensions = EXCLUDED.dimensions, ready = false
            '''), {"fingerprint": generation.fingerprint, "model": generation.model, "dimensions": generation.dimensions})
            # The upsert locks this generation. Publish replacement and readiness
            # together at COMMIT; failed seeds preserve a previously ready generation.
            connection.execute(text(f'DELETE FROM "{schema}".policy_chunks WHERE fingerprint = :fingerprint'),
                               {"fingerprint": generation.fingerprint})
            if records:
                connection.execute(text(f'''
                    INSERT INTO "{schema}".policy_chunks
                    (fingerprint, chunk_id, category, effective_from, effective_to, document, metadata, embedding)
                    VALUES (:fingerprint, :id, :category, :from, :to, :document, CAST(:metadata AS jsonb), CAST(:embedding AS public.vector))
                '''), [{"fingerprint": generation.fingerprint, "id": record.chunk_id,
                        "category": record.metadata["category"], "from": record.metadata["effective_from"],
                        "to": record.metadata["effective_to"], "document": record.text,
                        "metadata": json.dumps(record.metadata), "embedding": embedding}
                       for record, embedding in zip(records, vectors, strict=True)])
            connection.execute(text(
                f'UPDATE "{schema}".policy_generations '
                'SET ready = true, record_count = :record_count '
                'WHERE fingerprint = :fingerprint'
            ), {"fingerprint": generation.fingerprint, "record_count": generation.record_count})

    def generation(self, fingerprint: str) -> Generation | None:
        with self._engine().connect() as connection:
            row = connection.execute(text(f'SELECT fingerprint, model, dimensions, ready, record_count '
                                          f'FROM "{self.schema}".policy_generations WHERE fingerprint = :fingerprint'),
                                     {"fingerprint": fingerprint}).mappings().first()
            return Generation(**row) if row is not None else None

    def count(self, fingerprint: str) -> int:
        with self._engine().connect() as connection:
            return int(connection.execute(
                text(f'SELECT count(*) FROM "{self.schema}".policy_chunks WHERE fingerprint = :fingerprint'),
                {"fingerprint": fingerprint},
            ).scalar_one())

    def search(self, fingerprint: str, embedding: list[float], *, category: str,
               effective_date: date, top_k: int) -> list[SearchHit]:
        # Exact search over the filtered small corpus avoids ANN recall loss.
        with self._engine().connect() as connection:
            rows = connection.execute(text(f'''
                SELECT chunk_id, document, metadata,
                       embedding OPERATOR(public.<=>) CAST(:embedding AS public.vector) AS distance
                FROM "{self.schema}".policy_chunks
                WHERE fingerprint = :fingerprint AND category = :category
                  AND effective_from <= :day AND effective_to >= :day
                ORDER BY distance, chunk_id LIMIT :top_k
            '''), {"fingerprint": fingerprint, "embedding": vector_literal(embedding),
                   "category": category, "day": effective_date.toordinal(), "top_k": top_k}).mappings()
            return [SearchHit(row["chunk_id"], row["document"], row["metadata"], row["distance"]) for row in rows]

    def close(self) -> None:
        if self._pool is not None:
            self._pool.dispose()
            self._pool = None
