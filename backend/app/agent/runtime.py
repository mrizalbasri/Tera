"""Checkpoint connections, per-claim locks, and resource lifecycle ownership."""

import sqlite3
import re
import time
from contextlib import contextmanager
from hashlib import blake2b
from pathlib import Path
from threading import RLock, local
from weakref import WeakKeyDictionary, WeakValueDictionary, finalize

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from sqlalchemy.engine import make_url

from app.config import Settings
from app.errors import ApplicationError


class GraphResources:
    """One saver per repository bundle; locks span request-scoped services."""

    def __init__(
        self, path: str | None = None, *, database_url: str | None = None,
        schema: str = "langgraph", setup: bool = True, lock_timeout: float = 5.0,
        owner=None,
    ) -> None:
        self._guard = RLock()
        self._locks = WeakValueDictionary()
        self._held = local()
        self.database_url = database_url
        self.lock_timeout = lock_timeout
        self.owner = owner
        self.settings = None
        self.connection = None
        if database_url is not None:
            if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema) or schema in ("public", "pg_catalog", "information_schema"):
                raise ValueError("Checkpoint schema must be a separate lowercase PostgreSQL schema.")
            url = make_url(database_url).set(drivername="postgresql")
            self.connection = psycopg.connect(
                url.render_as_string(hide_password=False), autocommit=True,
                row_factory=dict_row, prepare_threshold=0, connect_timeout=5,
            )
            try:
                if setup:
                    self.connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
                self.connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                self.saver = PostgresSaver(self.connection)
                if setup:
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

    @contextmanager
    def claim_lock(self, claim_id, *, timeout: float | None = None):
        key = str(claim_id)
        timeout = self.lock_timeout if timeout is None else timeout
        with self._guard:
            lock = self._locks.setdefault(key, RLock())
        if not lock.acquire(timeout=timeout):
            raise ApplicationError("claim_busy", "Claim is being updated; retry shortly.", 409)
        held = getattr(self._held, "keys", set())
        connection = None
        outer = key not in held
        acquired = False
        number = None
        try:
            if outer and self.database_url:
                url = make_url(self.database_url).set(drivername="postgresql")
                connection = psycopg.connect(url.render_as_string(hide_password=False), autocommit=True, connect_timeout=5)
                number = int.from_bytes(blake2b(key.encode(), digest_size=8).digest(), "big", signed=True)
                deadline = time.monotonic() + timeout
                while not connection.execute("SELECT pg_try_advisory_lock(%s)", (number,)).fetchone()[0]:
                    if time.monotonic() >= deadline:
                        raise ApplicationError("claim_busy", "Claim is being updated; retry shortly.", 409)
                    time.sleep(0.025)
                acquired = True
            self._held.keys = held | {key}
            yield
        finally:
            if outer:
                self._held.keys = held
            if connection is not None:
                if acquired and number is not None:
                    try:
                        connection.execute("SELECT pg_advisory_unlock(%s)", (number,))
                    except Exception:
                        pass
                try:
                    connection.close()
                except Exception:
                    pass
            lock.release()

    def run_step(self, name, state, action):
        def execute():
            output = action()
            if self.owner is not None and hasattr(self.owner, "operational") and self.settings is not None:
                from uuid import UUID
                from app.services.notifications import NotificationService

                NotificationService(self.owner, self.settings).sync_claim(UUID(state["claim_id"]))
            return output

        if self.owner is not None and hasattr(self.owner, "atomic_step"):
            return self.owner.atomic_step(f"{state['run_id']}:{name}", execute)
        return execute()

    def transaction(self):
        from contextlib import nullcontext

        return self.owner.transaction() if hasattr(self.owner, "transaction") else nullcontext()

    def ready(self) -> None:
        if self.connection is not None:
            self.connection.execute("SELECT 1")
        # Read checkpoint tables too; SELECT 1 alone cannot detect missing setup.
        self.saver.get_tuple({"configurable": {"thread_id": "readiness"}})

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
                    setup=settings.environment != "production", lock_timeout=settings.claim_lock_timeout_seconds,
                    owner=owner,
                )
            else:
                path = settings.graph_checkpoint_path if settings.storage_backend == "sql" else None
                resources = GraphResources(path, lock_timeout=settings.claim_lock_timeout_seconds, owner=owner)
            _registry[owner] = resources
            resources.settings = settings
            finalize(owner, resources.close)
        return resources


def close_graph_resources() -> None:
    """Called at application shutdown and by isolated test/restart fixtures."""
    with _registry_lock:
        for resources in list(_registry.values()):
            resources.close()
        _registry.clear()
