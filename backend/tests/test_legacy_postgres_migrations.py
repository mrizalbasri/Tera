"""Migration regressions against disposable PostgreSQL databases."""

import pytest
from sqlalchemy import create_engine, event, inspect, select, text

from app.repositories.migrations import (
    CURRENT_VERSION, migration_metadata, require_current, schema_version, upgrade, versions,
)

ORDERED_TABLES = ("claims", "receipts", "processing_runs", "domain_records")


@pytest.mark.parametrize("legacy_version", [0, 1, 2])
def test_upgrade_backfills_legacy_order_columns(postgres_database_url, legacy_version):
    engine = create_engine(postgres_database_url)
    metadata = migration_metadata()
    try:
        with engine.begin() as connection:
            metadata.create_all(connection)
            versions.create(connection)
            for version in range(1, legacy_version + 1):
                connection.execute(versions.insert().values(version=version))
            for name in ORDERED_TABLES:
                connection.execute(text(f'ALTER TABLE "{name}" DROP COLUMN insertion_order'))
                values = {"id": "legacy", "payload": {"synthetic": True}}
                if name == "claims":
                    values.update(employee_id="synthetic", status="received")
                else:
                    values["claim_id"] = "legacy"
                if name == "receipts":
                    values["content_hash"] = "synthetic"
                if name == "domain_records":
                    values.update(kind="signal", created_at="2026-10-15T00:00:00Z")
                connection.execute(metadata.tables[name].insert().values(**values))
        upgrade(engine)
        upgrade(engine)
        require_current(engine)
        with engine.begin() as connection:
            assert schema_version(connection) == CURRENT_VERSION
            for name in ORDERED_TABLES:
                table = metadata.tables[name]
                columns = {c["name"]: c for c in inspect(connection).get_columns(name)}
                assert columns["insertion_order"]["identity"]
                assert columns["insertion_order"]["nullable"] is False
                legacy = connection.execute(select(table)).one()
                assert legacy.payload == {"synthetic": True}
                assert legacy.insertion_order > 0
                values = dict(legacy._mapping)
                del values["insertion_order"]
                values["id"] = "new"
                order = connection.scalar(table.insert().values(**values).returning(table.c.insertion_order))
                assert order > legacy.insertion_order
    finally:
        engine.dispose()


def test_failed_legacy_upgrade_does_not_stamp_version(postgres_database_url):
    engine = create_engine(postgres_database_url)
    try:
        upgrade(engine)
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM schema_migrations WHERE version = 3"))
            for name in ORDERED_TABLES:
                connection.execute(text(f'ALTER TABLE "{name}" DROP COLUMN insertion_order'))

        def fail_second_table(connection, cursor, statement, parameters, context, executemany):
            if 'ALTER TABLE "receipts" ADD COLUMN' in statement:
                raise RuntimeError("synthetic migration failure")

        event.listen(engine, "before_cursor_execute", fail_second_table)
        with pytest.raises(RuntimeError, match="synthetic migration failure"):
            upgrade(engine)
        event.remove(engine, "before_cursor_execute", fail_second_table)
        with engine.connect() as connection:
            assert schema_version(connection) == 2
            assert "insertion_order" not in {c["name"] for c in inspect(connection).get_columns("claims")}
        upgrade(engine)
        require_current(engine)
    finally:
        engine.dispose()
