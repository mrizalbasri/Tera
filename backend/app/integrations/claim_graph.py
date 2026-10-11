"""Local checkpoint ownership and the claim graph's control-only state."""

import sqlite3
import re
from pathlib import Path
from threading import RLock
from typing import TypedDict
from weakref import WeakKeyDictionary, finalize

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from sqlalchemy.engine import make_url

from app.config import Settings


class ClaimGraphState(TypedDict):
    claim_id: str
    run_id: str
    pipeline_version: str
    stage: str


class GraphResources:
    """One saver per repository bundle; locks span request-scoped services."""

    def __init__(
        self, path: str | None = None, *, database_url: str | None = None,
        schema: str = "langgraph",
    ) -> None:
        self._guard = RLock()
        self._locks: dict[str, RLock] = {}
        self.connection = None
        if database_url is not None:
            if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema) or schema in ("public", "pg_catalog", "information_schema"):
                raise ValueError("Checkpoint schema must be a separate lowercase PostgreSQL schema.")
            url = make_url(database_url).set(drivername="postgresql")
            self.connection = psycopg.connect(
                url.render_as_string(hide_password=False), autocommit=True,
                row_factory=dict_row, prepare_threshold=0,
            )
            try:
                self.connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
                self.connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                self.saver = PostgresSaver(self.connection)
                self.saver.setup()
            except BaseException:
                self.close()
                raise
        elif path is None:
            self.saver = InMemorySaver()
        else:
            Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(path, check_same_thread=False)
            self.saver = SqliteSaver(self.connection)
            self.saver.setup()

    def claim_lock(self, claim_id) -> RLock:
        with self._guard:
            return self._locks.setdefault(str(claim_id), RLock())

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None


_registry: WeakKeyDictionary = WeakKeyDictionary()
_registry_lock = RLock()


def graph_resources(owner, settings: Settings) -> GraphResources:
    with _registry_lock:
        resources = _registry.get(owner)
        if resources is None:
            if settings.storage_backend == "sql" and make_url(settings.database_url).get_backend_name() == "postgresql":
                resources = GraphResources(
                    database_url=settings.database_url, schema=settings.graph_checkpoint_schema,
                )
            else:
                path = settings.graph_checkpoint_path if settings.storage_backend == "sql" else None
                resources = GraphResources(path)
            _registry[owner] = resources
            finalize(owner, resources.close)
        return resources


def close_graph_resources() -> None:
    """Called at application shutdown and by isolated test/restart fixtures."""
    with _registry_lock:
        for resources in list(_registry.values()):
            resources.close()
        _registry.clear()
