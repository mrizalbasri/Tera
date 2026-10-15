"""Operational regressions use synthetic receipts and disposable databases."""


from datetime import UTC, datetime, timedelta


from uuid import UUID, uuid4


from concurrent.futures import ThreadPoolExecutor


from io import BytesIO


import os


from pathlib import Path


import subprocess


import sys


import pytest


from fastapi.testclient import TestClient


from sqlalchemy import create_engine, event, inspect, text


from app.api import deps


from app.agent.nodes import ClaimNodes


from app.agent.runtime import GraphResources, close_graph_resources


from app.config import Settings, get_settings


from app.errors import ApplicationError


from app.main import app


from app.repositories.migrations import CURRENT_VERSION, require_current, schema_version, upgrade


from app.repositories.query import ClaimFilter


from app.repositories.sql import SqlRepositories


from app.schemas.core import Claim


@pytest.fixture(params=["sqlite", "postgres"])
def persistent(request, tmp_path):
    url = request.getfixturevalue("postgres_database_url") if request.param == "postgres" else f"sqlite:///{tmp_path / 'claims.db'}"
    settings = Settings(_env_file=None, storage_backend="sql", database_url=url,
                        graph_checkpoint_path=str(tmp_path / "graph.db"))
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def create(client, marker="normal", amount="60000"):
    response = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": amount},
                           files={"files": ("synthetic.pdf", BytesIO(f"%PDF-1.7\n{marker}".encode()), "application/pdf")})
    assert response.status_code == 201, response.text
    return UUID(response.json()["claim"]["id"])


def test_migration_is_repeatable_preserves_existing_data_and_checks_version(persistent):
    backend = deps._backend(persistent)
    claim_id = create(TestClient(app))
    upgrade(backend._engine)
    upgrade(backend._engine)
    assert backend.claims.get(claim_id) is not None
    with backend._engine.begin() as connection:
        assert schema_version(connection) == CURRENT_VERSION
        connection.execute(text("DELETE FROM schema_migrations WHERE version = 2"))
    with pytest.raises(RuntimeError, match="not current"):
        SqlRepositories(persistent.database_url, initialize_schema=False)
    upgrade(backend._engine)
    require_current(backend._engine)


def test_legacy_sqlite_migration_keeps_payload_and_adds_order(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE claims (id VARCHAR(36) PRIMARY KEY, employee_id VARCHAR(100), status VARCHAR(40), payload JSON)"))
        connection.execute(text("INSERT INTO claims VALUES ('legacy', 'synthetic', 'received', '{}')"))
    upgrade(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT employee_id FROM claims WHERE id = 'legacy'")) == "synthetic"
        assert "insertion_order" in {c["name"] for c in inspect(connection).get_columns("claims")}
    engine.dispose()


def test_rolled_back_inner_repository_call_cannot_commit_partial_state(persistent):
    backend = deps._backend(persistent)
    with pytest.raises(RuntimeError, match="rolled back"):
        with backend.transaction() as session:
            session.rollback()
            session.execute(text("INSERT INTO workflow_steps (key, payload) VALUES ('invalid', '{}')"))
    with backend._engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM workflow_steps WHERE key = 'invalid'")) == 0
