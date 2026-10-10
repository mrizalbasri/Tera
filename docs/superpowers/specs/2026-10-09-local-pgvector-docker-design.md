# Local pgvector with Docker

The owner approved Docker instead of installing Windows C++ Build Tools.
Use the official pgvector PostgreSQL 18 image, pinned to 0.8.7-pg18-bookworm,
with Compose project tera, one postgres service and a named data volume mounted
at /var/lib/postgresql (PostgreSQL 18 layout). Publish only 127.0.0.1:5434;
the native PostgreSQL service on 5432 and its data remain unchanged.

Credentials live in ignored backend/data/local/postgres.env. Update only the
database/storage/RAG configuration in the existing ignored backend/.env,
preserving provider settings and making an ignored backup first. The Docker
database starts empty; existing native claims are not automatically migrated.

Start Docker Desktop, start Compose with a readiness healthcheck, create the
vector extension in tera and verify server/extension versions. Run the full
backend suite against disposable databases on port 5434 with fake models. Seed
the canonical policy corpus using cached real embedding/reranker models, verify
five-category parity and benchmark. Enable RAG only after successful seed and
restart the database once to verify persisted policy data. No system compiler,
CI changes, frontend changes or merge are included.

Document DBeaver connection, start/stop commands, persistent volume behavior and
the distinction between the native and Docker databases. Never remove the data
volume as part of routine shutdown. If Docker cannot start, preserve configuration
and report its concrete blocker without claiming successful runtime validation.

## Completed validation — 2026-10-10

Port 5433 was occupied by prism-db after Docker startup, so Tera uses 5434.
The service is healthy, PostgreSQL 18.6/vector 0.8.7 are verified, and all 15
policy chunks persisted through container restart. The full suite passed
369 tests, with only the missing-extension case skipped. Offline real-model
seed, five-policy parity and nine-case reranking benchmark passed. The ignored
backend environment is backed up and points to the Docker database; provider
settings are preserved. See [[development/pgvector]] for operations and results.
