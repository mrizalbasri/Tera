"""Create, dump and restore disposable synthetic PostgreSQL databases only."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.agent.runtime import close_graph_resources, graph_resources
from app.api import deps
from app.config import Settings
from app.services.intake import IntakeService, ReceiptUpload
from app.integrations.quality import FileQualityChecker
from app.services.recovery import build_processing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/local/evaluation/restore.json"))
    args = parser.parse_args()
    configured = os.environ.get("TEST_POSTGRES_URL")
    if not configured:
        parser.error("Set TEST_POSTGRES_URL to a dedicated test server; application DATABASE_URL is never used")
    url = make_url(configured).set(drivername="postgresql")
    prefix = "tera_restore_" + uuid4().hex
    source, target = prefix + "_source", prefix + "_target"
    tool_paths = {}
    for tool in ("pg_dump", "pg_restore"):
        path = args.pg_bin / tool if args.pg_bin else None
        if path and os.name == "nt":
            path = path.with_suffix(".exe")
        found = str(path) if path and path.is_file() else shutil.which(tool)
        if not found:
            parser.error(f"{tool} is unavailable; use --pg-bin")
        tool_paths[tool] = found
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    connection_args = ["--host", url.host or "localhost", "--port", str(url.port or 5432), "--username", url.username or "postgres"]
    created = []
    report = {"synthetic": True, "passed": False, "evaluated_at": datetime.now(UTC).isoformat()}
    with psycopg.connect(url.render_as_string(hide_password=False), autocommit=True) as admin:
        try:
            for name in (source, target):
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                created.append(name)
            settings = Settings(_env_file=None, environment="test", storage_backend="sql", demo_mode=False,
                database_url=url.set(drivername="postgresql+psycopg", database=source).render_as_string(hide_password=False),
                provider_mode="mock", policy_mode="local", anomaly_mode="rules")
            backend = deps._backend(settings)
            processing = build_processing(settings)
            intake = IntakeService(backend.claims, backend.receipts, backend.file_storage, FileQualityChecker(), backend.audit,
                                   settings, graph_resources(backend, settings))
            claims = []
            for marker in ("CATEGORY:MEALS", "LOW_CONFIDENCE"):
                claim, receipts, _ = intake.create_claim(employee_id="synthetic-restore", currency="IDR", declared_amount=Decimal("60000"),
                    files=[ReceiptUpload(filename="synthetic.pdf", media_type="application/pdf",
                                         content=f"%PDF-1.7\n{marker}\n%%EOF".encode())], idempotency_key=None)
                processing.process_claim(claim.id)
                claims.append((claim.id, receipts[0].storage_reference))
            with psycopg.connect(url.set(database=source).render_as_string(hide_password=False), autocommit=True) as connection:
                connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
                connection.execute("CREATE SCHEMA rag_restore_probe")
                connection.execute("CREATE TABLE rag_restore_probe.chunks (id integer PRIMARY KEY, embedding vector(3))")
                connection.execute("INSERT INTO rag_restore_probe.chunks VALUES (1, '[1,0,0]')")
            close_graph_resources()
            deps.close_sql_repositories()
            with tempfile.TemporaryDirectory(prefix="tera-restore-") as directory:
                archive = Path(directory) / "synthetic.dump"
                subprocess.run([tool_paths["pg_dump"], *connection_args, "--dbname", source, "--format", "custom", "--file", str(archive)],
                               env=env, check=True, capture_output=True)
                subprocess.run([tool_paths["pg_restore"], *connection_args, "--dbname", target, "--no-owner", "--exit-on-error", str(archive)],
                               env=env, check=True, capture_output=True)
            restored_settings = settings.model_copy(update={"database_url": url.set(drivername="postgresql+psycopg", database=target).render_as_string(hide_password=False)})
            restored = deps._backend(restored_settings)
            restored.ready()
            restored_processing = build_processing(restored_settings)
            assert [restored.claims.get(id).status for id, _ in claims] == ["approved", "needs_clarification"]
            for id, storage_reference in claims:
                assert restored.file_storage.get(storage_reference).startswith(b"%PDF-")
                assert restored_processing.process_claim(id).claim.id == id
                assert restored_processing.graph.get_state({"configurable": {"thread_id": str(id)}}).values
            assert len(restored.decisions.list_for_claim(claims[0][0])) == 1
            assert restored.operational.list("notifications", owner="synthetic-restore")
            with psycopg.connect(url.set(database=target).render_as_string(hide_password=False)) as connection:
                assert connection.execute("SELECT count(*) FROM rag_restore_probe.chunks").fetchone()[0] == 1
            report.update(passed=True, claim_count=len(claims), receipt_content=True, decisions=True,
                          checkpoints=True, notifications=True, vector_schema_probe=True, replay_without_duplicate_decision=True)
        finally:
            close_graph_resources()
            deps.close_sql_repositories()
            for name in reversed(created):
                # Every name is generated above and CREATE DATABASE succeeded in this invocation.
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
