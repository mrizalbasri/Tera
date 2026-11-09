"""Additive, numbered domain migrations. Production runs these before startup."""

import hashlib
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, Identity, Integer, JSON, LargeBinary, MetaData, String, Table, UniqueConstraint, inspect, select, text
from sqlalchemy.engine import Connection, Engine

CURRENT_VERSION = 5
versions = Table("schema_migrations", MetaData(), Column("version", Integer, primary_key=True))
BASELINE_TABLES = (
    "claims", "receipts", "file_storage", "processing_runs", "domain_records",
    "conversation_context", "idempotency_keys", "audit_events",
)


def hash_password(password: str) -> str:
    salt = "tera_demo_salt"
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2_sha256${salt}${h}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash == password:
        return True
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$")
        if len(parts) == 3:
            salt = parts[1]
            expected = parts[2]
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
            return actual == expected
    return False


def migration_metadata() -> MetaData:
    """Frozen v1/v2 definitions; future models must not rewrite old migrations."""
    metadata = MetaData()

    def ordered(name, *columns):
        return Table(name, metadata, Column("insertion_order", BigInteger, Identity(), nullable=False), *columns)

    def identifier(name="id", *, primary_key=False, index=False):
        return Column(name, String(36), primary_key=primary_key, nullable=False, index=index)

    def payload():
        return Column("payload", JSON, nullable=False)

    ordered("claims", identifier(primary_key=True), Column("employee_id", String(100), nullable=False, index=True),
            Column("status", String(40), nullable=False, index=True), payload())
    ordered("receipts", identifier(primary_key=True), identifier("claim_id", index=True),
            Column("content_hash", String(64), nullable=False, index=True), payload())
    Table("file_storage", metadata, Column("reference", String(200), primary_key=True), Column("content", LargeBinary, nullable=False))
    ordered("processing_runs", identifier(primary_key=True), identifier("claim_id", index=True), payload())
    ordered("domain_records", identifier(primary_key=True), identifier("claim_id", index=True),
            Column("kind", String(40), index=True, nullable=False), Column("created_at", String(40), nullable=False), payload())
    Table("conversation_context", metadata, Column("id", Integer, primary_key=True, autoincrement=True),
          identifier("claim_id", index=True), payload())
    Table("idempotency_keys", metadata, Column("key", String(200), primary_key=True), identifier("target_id"))
    Table("audit_events", metadata, identifier(primary_key=True), Column("aggregate_type", String(100), nullable=False),
          Column("aggregate_id", String(36), nullable=False, index=True), Column("sequence_number", Integer, nullable=False), payload(),
          UniqueConstraint("aggregate_type", "aggregate_id", "sequence_number", name="uq_audit_sequence"))
    Table("workflow_steps", metadata, Column("key", String(100), primary_key=True), payload())
    Table("api_rate_limits", metadata, Column("key", String(64), primary_key=True),
          Column("window", BigInteger, index=True, nullable=False), Column("count", Integer, nullable=False))
    Table("operational_records", metadata, identifier(primary_key=True),
          Column("namespace", String(100), index=True, nullable=False),
          Column("owner", String(100), index=True, nullable=False),
          Column("aggregate_id", String(100), index=True, nullable=False),
          Column("created_at", String(40), index=True, nullable=False),
          Column("revision", Integer, nullable=False), payload())
    Table("users", metadata,
          Column("id", String(36), primary_key=True),
          Column("username", String(100), unique=True, nullable=False, index=True),
          Column("email", String(100), unique=True, nullable=False, index=True),
          Column("password_hash", String(200), nullable=False),
          Column("role", String(20), nullable=False),
          Column("created_at", String(40), nullable=False))
    return metadata


def schema_version(connection: Connection) -> int:
    if not inspect(connection).has_table("schema_migrations"):
        return 0
    return max(connection.scalars(select(versions.c.version)), default=0)


def require_current(engine: Engine) -> None:
    with engine.connect() as connection:
        if schema_version(connection) != CURRENT_VERSION:
            raise RuntimeError("Database schema is not current; run python -m app.migrate.")


def _add_order_columns(connection: Connection) -> None:
    for name in ("claims", "receipts", "processing_runs", "domain_records"):
        if "insertion_order" in {c["name"] for c in inspect(connection).get_columns(name)}:
            continue
        definition = "BIGINT"
        if connection.dialect.name == "postgresql":
            definition = "BIGINT GENERATED BY DEFAULT AS IDENTITY NOT NULL"
        connection.execute(text(f'ALTER TABLE "{name}" ADD COLUMN insertion_order {definition}'))


def _seed_default_users(connection: Connection, users_table: Table) -> None:
    now = datetime.now(timezone.utc).isoformat()
    demo_pass = hash_password("demo123")
    default_users = [
        ("usr_admin_email", "admin@tera.id", "admin@tera.id", demo_pass, "admin"),
        ("usr_finance_email", "finance@tera.id", "finance@tera.id", demo_pass, "admin"),
        ("usr_reviewer_email", "reviewer@tera.id", "reviewer@tera.id", demo_pass, "admin"),
        ("usr_karyawan_email", "karyawan@tera.id", "karyawan@tera.id", demo_pass, "member"),
        ("usr_salesman_email", "salesman-001@tera.id", "salesman-001@tera.id", demo_pass, "member"),
        # Short aliases:
        ("usr_admin_alias", "admin", "admin@tera.local", demo_pass, "admin"),
        ("usr_finance_alias", "finance", "finance@tera.local", demo_pass, "admin"),
        ("usr_reviewer_alias", "reviewer", "reviewer@tera.local", demo_pass, "admin"),
        ("usr_karyawan_alias", "karyawan", "karyawan@tera.local", demo_pass, "member"),
        ("usr_salesman_alias", "salesman-001", "salesman-001@tera.local", demo_pass, "member"),
    ]
    for uid, username, email, pwd, role in default_users:
        exists = connection.scalar(select(users_table.c.id).where(users_table.c.username == username))
        if not exists:
            connection.execute(users_table.insert().values(
                id=uid, username=username, email=email, password_hash=pwd, role=role, created_at=now
            ))


def upgrade(engine: Engine) -> None:
    # Import registers the SQLite compatibility compiler for the order column.
    from app.repositories import sql as _sql  # noqa: F401

    metadata = migration_metadata()

    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(742901, 1)"))
        versions.create(connection, checkfirst=True)
        version = schema_version(connection)
        if version > CURRENT_VERSION:
            raise RuntimeError("Database schema is newer than this application.")
        if version < 1:
            metadata.create_all(connection, tables=[metadata.tables[name] for name in BASELINE_TABLES])
            _add_order_columns(connection)
            connection.execute(versions.insert().values(version=1))
        if version < 2:
            metadata.create_all(connection, tables=[metadata.tables[name] for name in ("workflow_steps", "api_rate_limits")])
            connection.execute(versions.insert().values(version=2))
        if version < 3:
            # Repair databases stamped v1/v2 before PostgreSQL legacy support.
            _add_order_columns(connection)
            connection.execute(versions.insert().values(version=3))
        if version < 4:
            metadata.tables["operational_records"].create(connection, checkfirst=True)
            connection.execute(versions.insert().values(version=4))
        if version < 5:
            metadata.tables["users"].create(connection, checkfirst=True)
            _seed_default_users(connection, metadata.tables["users"])
            connection.execute(versions.insert().values(version=5))
