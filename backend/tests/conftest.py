import tempfile
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings

# Disable dotenv before app.main creates its module-level settings at collection.
# Individual tests still supply their own isolated settings and providers.
Settings.model_config["env_file"] = None

from app.main import app
from app.agent.runtime import close_graph_resources
from app.integrations.rag.pgvector import close_policy_indexes
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


@pytest.fixture(autouse=True)
def isolated_stores(monkeypatch):
    """No local .env/provider calls; independent domain and graph stores."""
    close_graph_resources()
    close_policy_indexes()
    deps.close_sql_repositories()
    deps._memory_repositories.cache_clear()
    deps._sql_repositories.cache_clear()
    get_settings.cache_clear()
    deps._rag_policy_retriever.cache_clear()
    deps._ml_anomaly_scorer.cache_clear()
    with tempfile.TemporaryDirectory(prefix="tera-graph-test-") as directory:
        monkeypatch.setenv("GRAPH_CHECKPOINT_PATH", f"{directory}/checkpoints.db")
        settings = Settings(_env_file=None, storage_backend="memory", provider_mode="mock", policy_mode="local", anomaly_mode="rules")
        app.dependency_overrides[get_settings] = lambda: settings
        try:
            yield
        finally:
            app.dependency_overrides.pop(get_settings, None)
            close_graph_resources()
            close_policy_indexes()
            deps.close_sql_repositories()
            deps._memory_repositories.cache_clear()
            deps._sql_repositories.cache_clear()
            get_settings.cache_clear()
            deps._rag_policy_retriever.cache_clear()
            deps._ml_anomaly_scorer.cache_clear()


@pytest.fixture
def postgres_database_url():
    """Create and remove only our own isolated database on the test server."""
    source = os.environ.get("TEST_POSTGRES_URL")
    if not source:
        pytest.skip("TEST_POSTGRES_URL is required for PostgreSQL integration tests")
    url = make_url(source).set(drivername="postgresql")
    name = "tera_test_" + uuid4().hex
    with psycopg.connect(url.render_as_string(hide_password=False), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield url.set(drivername="postgresql+psycopg", database=name).render_as_string(hide_password=False)
        finally:
            close_graph_resources()
            close_policy_indexes()
            deps.close_sql_repositories()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def limited_size_client() -> TestClient:
    """Client whose receipt size limit is small enough to test cheaply."""
    settings = Settings(_env_file=None, max_receipt_size_bytes=64)
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)
