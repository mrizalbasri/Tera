"""pgvector validation plus optional real-server tests on isolated databases."""

from datetime import date
from types import SimpleNamespace
import os
import subprocess
import sys

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.config import Settings
from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS
from app.integrations.rag.index import seed_index
from app.integrations.rag.pgvector import PgPolicyStore, close_policy_indexes, vector_literal
from app.integrations.rag.retriever import RagPolicyRetriever
from rag_fakes import FakeEmbedder, MemoryVectorStore


@pytest.mark.parametrize("vector", [[], [0, 0, 0], [float("nan"), 1], [float("inf"), 1],
    [float("-inf"), 1], [1e40, 1], [True, 1], [None, 1], ["invalid", 1]])
def test_invalid_vectors_are_rejected(vector) -> None:
    with pytest.raises((ValueError, TypeError)):
        vector_literal(vector)


def test_vector_serialization_is_finite_dimension_checked_and_parameter_safe() -> None:
    assert vector_literal([1, -0.25, 0.5], 3) == "[1.0,-0.25,0.5]"
    with pytest.raises(ValueError, match="invalid_embedding_dimensions"):
        vector_literal([1, 2], 3)
    with pytest.raises(ValueError):
        vector_literal(["1); DROP TABLE policy_chunks;--"])


@pytest.mark.parametrize("schema", ["public", "pg_catalog", "information_schema", "langgraph", "Rag", "rag;drop", "a"*64, ""])
def test_schema_settings_reject_shared_or_unsafe_identifiers(schema) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, policy_index_schema=schema)


def test_legacy_path_setting_is_accepted_but_not_used() -> None:
    settings = Settings(_env_file=None, policy_index_path="legacy/ignored/path")
    assert settings.policy_index_schema == "rag"
    assert "policy_index_path" not in settings.model_dump()


@pytest.mark.parametrize("bad_vectors", [[], [[1, 2]]*15, [[0, 0, 0]]*15, [[1, 2, float("nan")]]*15])
def test_seed_validates_vectors_before_writing(bad_vectors) -> None:
    store = MemoryVectorStore()
    # The 2D non-zero case is valid; force one inconsistent dimension.
    if bad_vectors and bad_vectors[0] == [1, 2]:
        bad_vectors = [[1, 2]] + [[1, 2, 3]]*14
    with pytest.raises(ValueError):
        seed_index("unused", SimpleNamespace(embed=lambda texts: bad_vectors), store=store)
    assert store.generations == {} and store.records == {}


def test_database_failure_is_classified_without_credentials_or_model_load(monkeypatch, caplog) -> None:
    store = MemoryVectorStore()
    def fail(*args):
        raise RuntimeError("postgresql://synthetic:credential-secret@host/private@example.test")
    store.generation = fail
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", lambda *args: pytest.fail("must not load"))
    result = RagPolicyRetriever("unused", "unused", store=store).retrieve_with_provenance(
        category="meals", effective_date=date.today(),
    )
    assert result.source == "local" and result.reason == "index_unavailable"
    assert "credential-secret" not in str(result.audit_payload()) + caplog.text
    assert "private@example.test" not in str(result.audit_payload()) + caplog.text


def test_pool_is_disposed_on_shutdown_and_can_be_reopened() -> None:
    store = PgPolicyStore("postgresql+psycopg://synthetic:placeholder@127.0.0.1/unused")
    calls = []
    store._pool = SimpleNamespace(dispose=lambda: calls.append("closed"))
    close_policy_indexes()
    assert calls == ["closed"] and store._pool is None
    close_policy_indexes()
    assert calls == ["closed"]


def _connect(database_url):
    return psycopg.connect(make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True)


@pytest.fixture
def vector_database_url(postgres_database_url):
    with _connect(postgres_database_url) as connection:
        available = connection.execute("SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name='vector')").fetchone()[0]
        if not available:
            pytest.skip("Install pgvector on the local PostgreSQL server, then rerun these integration tests")
    return postgres_database_url


def test_unseeded_postgres_request_does_not_create_schema(postgres_database_url, monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.rag.search.SentenceEmbedder", lambda *args: pytest.fail("must not load"))
    rag = RagPolicyRetriever(postgres_database_url, "unused", index_schema="rag_unseeded")
    result = rag.retrieve_with_provenance(category="meals", effective_date=date.today())
    assert result.reason == "index_unavailable" and result.source == "local"
    with _connect(postgres_database_url) as connection:
        assert connection.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='rag_unseeded')").fetchone()[0] is False


def test_missing_server_extension_seed_rolls_back_all_ddl(postgres_database_url) -> None:
    with _connect(postgres_database_url) as connection:
        if connection.execute("SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name='vector')").fetchone()[0]:
            pytest.skip("Only applies to a server without pgvector installed")
    with pytest.raises(DBAPIError):
        seed_index(postgres_database_url, FakeEmbedder())
    with _connect(postgres_database_url) as connection:
        assert connection.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='rag')").fetchone()[0] is False


def test_pgvector_repeat_seed_restart_and_category_parity(vector_database_url) -> None:
    first = seed_index(vector_database_url, FakeEmbedder())
    assert seed_index(vector_database_url, FakeEmbedder()) == first
    store = PgPolicyStore(vector_database_url)
    with store._engine().connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM rag.policy_chunks WHERE fingerprint=:f'), {"f": first}).scalar_one() == 15
    store.close()
    restarted = RagPolicyRetriever(vector_database_url, "unused", embedder=FakeEmbedder())
    for category in CATEGORY_DESCRIPTIONS:
        selected = restarted.retrieve_with_provenance(category=category, effective_date=date(2026, 1, 1))
        assert selected.source == "rag" and selected.policy.category == category


def test_pgvector_filters_and_exact_cosine_order(vector_database_url) -> None:
    seed_index(vector_database_url, FakeEmbedder())
    rag = RagPolicyRetriever(vector_database_url, "unused", embedder=FakeEmbedder())
    store = rag._index.store
    hits = store.search(rag.fingerprint, [1, 0.25, 0.5], category="fuel", effective_date=date(2026, 1, 1), top_k=2)
    assert len(hits) == 2 and all(hit.metadata["category"] == "fuel" for hit in hits)
    assert hits == sorted(hits, key=lambda hit: (hit.distance, hit.chunk_id))
    assert store.search(rag.fingerprint, [1, 0.25, 0.5], category="fuel", effective_date=date(2025, 12, 31), top_k=8) == []


def test_pgvector_failed_reseed_preserves_previous_generation(vector_database_url) -> None:
    from sqlalchemy.exc import IntegrityError

    memory = MemoryVectorStore()
    fingerprint = seed_index("unused", FakeEmbedder(), store=memory)
    store = PgPolicyStore(vector_database_url)
    generation, records = memory.generations[fingerprint], memory.records[fingerprint]
    store.seed(generation, records)
    with pytest.raises(IntegrityError):
        store.seed(generation, [records[0], records[0]])
    assert store.generation(fingerprint) == generation
    with store._engine().connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM rag.policy_chunks WHERE fingerprint=:f'), {"f": fingerprint}).scalar_one() == 15


def test_pgvector_model_generations_with_different_dimensions_are_isolated(vector_database_url) -> None:
    first = seed_index(vector_database_url, FakeEmbedder())
    four = SimpleNamespace(embed=lambda texts: [[1, 0.5, 0.3, 0.2] for text in texts])
    second = seed_index(vector_database_url, four, model_identity="synthetic-four-dimensions")
    assert first != second
    for embedder, model in [(FakeEmbedder(), None), (four, "synthetic-four-dimensions")]:
        kwargs = {"model_identity": model} if model else {}
        rag = RagPolicyRetriever(vector_database_url, "unused", embedder=embedder, **kwargs)
        assert rag.retrieve_with_provenance(category="meals", effective_date=date.today()).source == "rag"


def test_pgvector_index_reopens_in_separate_process(vector_database_url) -> None:
    seed_index(vector_database_url, FakeEmbedder())
    # Pass the disposable test DSN in the subprocess environment, never argv/output.
    environment = dict(os.environ, RAG_TEST_DATABASE_URL=vector_database_url)
    script = '''
import os
from datetime import date
from app.integrations.rag.corpus import CATEGORY_DESCRIPTIONS
from app.integrations.rag.retriever import RagPolicyRetriever
from rag_fakes import FakeEmbedder
retriever = RagPolicyRetriever(os.environ['RAG_TEST_DATABASE_URL'], 'unused', embedder=FakeEmbedder())
for category in CATEGORY_DESCRIPTIONS:
    selected = retriever.retrieve_with_provenance(category=category, effective_date=date.today())
    assert selected.source == 'rag', selected.reason
print('all categories retrieved')
'''
    environment["PYTHONPATH"] = os.pathsep.join([os.path.abspath("tests"), os.path.abspath(".")])
    result = subprocess.run([sys.executable, "-c", script], env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "all categories retrieved" in result.stdout
