"""Versioned records for inbox state and policy publication."""

from copy import deepcopy
from threading import RLock
from typing import Protocol

from sqlalchemy import select, update

from app.errors import ApplicationError


class OperationalStore(Protocol):
    def get(self, key: str) -> dict | None: ...
    def list(self, namespace: str, *, owner: str | None = None, aggregate_id: str | None = None,
             limit: int = 200, offset: int = 0) -> list[dict]: ...
    def insert(self, record: dict) -> dict: ...
    def replace(self, record: dict, *, revision: int) -> dict: ...


def conflict() -> ApplicationError:
    return ApplicationError("record_changed", "Data sudah berubah. Muat ulang sebelum menyimpan.", 409)


class MemoryOperationalStore:
    def __init__(self) -> None:
        self._records: dict[str, dict] = {}
        self._lock = RLock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            return deepcopy(self._records.get(key))

    def list(self, namespace: str, *, owner: str | None = None, aggregate_id: str | None = None,
             limit: int = 200, offset: int = 0) -> list[dict]:
        with self._lock:
            rows = [r for r in self._records.values() if r["namespace"] == namespace
                    and (owner is None or r["owner"] == owner)
                    and (aggregate_id is None or r["aggregate_id"] == aggregate_id)]
            return deepcopy(sorted(rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)[offset:offset + limit])

    def insert(self, record: dict) -> dict:
        with self._lock:
            return deepcopy(self._records.setdefault(record["id"], deepcopy(record)))

    def replace(self, record: dict, *, revision: int) -> dict:
        with self._lock:
            current = self._records.get(record["id"])
            if current is None or current["revision"] != revision:
                raise conflict()
            saved = {**deepcopy(record), "revision": revision + 1}
            self._records[record["id"]] = saved
            return deepcopy(saved)


class SqlOperationalStore:
    def __init__(self, sessions, row_type) -> None:
        self._sessions, self._row = sessions, row_type

    @staticmethod
    def _record(row) -> dict:
        return {"id": row.id, "namespace": row.namespace, "owner": row.owner,
                "aggregate_id": row.aggregate_id, "created_at": row.created_at,
                "revision": row.revision, "payload": deepcopy(row.payload)}

    def get(self, key: str) -> dict | None:
        with self._sessions() as session:
            row = session.get(self._row, key)
            return self._record(row) if row else None

    def list(self, namespace: str, *, owner: str | None = None, aggregate_id: str | None = None,
             limit: int = 200, offset: int = 0) -> list[dict]:
        with self._sessions() as session:
            stmt = select(self._row).where(self._row.namespace == namespace)
            if owner is not None:
                stmt = stmt.where(self._row.owner == owner)
            if aggregate_id is not None:
                stmt = stmt.where(self._row.aggregate_id == aggregate_id)
            stmt = stmt.order_by(self._row.created_at.desc(), self._row.id.desc()).limit(limit).offset(offset)
            return [self._record(row) for row in session.scalars(stmt)]

    def insert(self, record: dict) -> dict:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        with self._sessions() as session:
            insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
            session.execute(insert(self._row).values(**record).on_conflict_do_nothing(index_elements=["id"]))
            session.commit()
            row = session.get(self._row, record["id"])
            return self._record(row)

    def replace(self, record: dict, *, revision: int) -> dict:
        with self._sessions() as session:
            result = session.execute(update(self._row).where(self._row.id == record["id"], self._row.revision == revision)
                                     .values(payload=record["payload"], revision=revision + 1))
            if result.rowcount != 1:
                raise conflict()
            session.commit()
            return {**record, "revision": revision + 1}
