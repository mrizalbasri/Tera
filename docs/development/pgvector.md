# PostgreSQL + pgvector for policy retrieval

Tera stores claims in PostgreSQL, checkpoints in `langgraph`, and policy vectors
in `rag` (configurable with `POLICY_INDEX_SCHEMA`). pgvector is a **PostgreSQL
server extension**, not a Python embedding model. This replaces the Chroma
adapter in the modular RAG PR; existing local Chroma files are left untouched.

## Docker local setup (selected for this project)

Docker replaces native compilation for Tera development. Keep the native Windows
PostgreSQL service on 5432; Compose creates a separate PostgreSQL 18 database on
**127.0.0.1:5434**, using `pgvector/pgvector:0.8.7-pg18-bookworm`. No C++ Build
Tools are needed. Existing native database contents are not copied automatically.

Start Docker Desktop and wait for its engine to run. From the repository root,
prepare credentials once (the actual setup already created this ignored file):

```powershell
New-Item -ItemType Directory -Force backend/data/local | Out-Null
Copy-Item docker/postgres.env.example backend/data/local/postgres.env
```

Replace the placeholder password in `backend/data/local/postgres.env` before
starting. On an already configured machine, preserve the existing file instead
of copying the example over it. The initial local setup reuses the existing
database password; credentials are not committed. Then run:

```powershell
docker compose up -d --wait --wait-timeout 90 postgres
docker compose exec -T postgres psql -U postgres -d tera -c "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;"
docker compose exec -T postgres psql -U postgres -d tera -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Set `DATABASE_URL` in `backend/.env` to
`postgresql+psycopg://postgres:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5434/tera` and
`STORAGE_BACKEND=sql`; preserve your extraction provider settings. Follow the
seed/verify section below before enabling RAG. DBeaver uses host `127.0.0.1`,
port `5434`, database `tera`, user `postgres` and the password from the ignored
Docker credentials file. This is a new connection distinct from port 5432.

The named Compose volume `tera_postgres_data` persists the PostgreSQL 18 data
under `/var/lib/postgresql`. `docker compose stop` stops the database;
`docker compose start` starts it again. `docker compose down` removes containers
but retains the volume. **Do not use `down -v` for routine shutdown: it deletes
the database volume.** Changing the password environment variable does not
change credentials inside an existing initialized volume; use PostgreSQL role
management for password rotation. The service binds only to IPv4 loopback.

If Docker reports a missing `SOFTWARE\\Docker Inc.\\Docker Desktop` registry
entry, start Docker Desktop from the Windows Start Menu and check engine status.
If that also fails, repair/reinstall Docker Desktop before running Compose; the
Compose configuration alone cannot run a stopped or broken engine.

## Seed and enable RAG

Keep the existing provider/model settings in `backend/.env`. Use the existing
PostgreSQL `DATABASE_URL` and add `POLICY_INDEX_SCHEMA=rag`. Password characters
in the URL must be URL-encoded. Never commit `.env` or paste credentials into
commands shared publicly. The schema must differ from the checkpoint schema.

Stop the API. From `backend/`, with the virtual environment activated:

```powershell
python -m pip install -r requirements.txt
python -m app.seed_policy --with-reranker --verify --benchmark
```

Seed is the only operation that creates schemas/tables or downloads the pinned
models. It requires extension/schema/table creation permissions. If the model
caches are already complete, run with `$env:HF_HUB_OFFLINE='1'`; this disables
Hugging Face network downloads, while PostgreSQL connections remain necessary.
No extraction LLM endpoint or API key is used by this command.

Verification must report RAG retrieval parity for all five categories, rather
than successful local fallback. The benchmark measures evidence relevance and
latency, not approval accuracy. After successful verification set:

```dotenv
POLICY_MODE=rag
POLICY_INDEX_SCHEMA=rag
POLICY_RERANK_MODE=cross_encoder
POLICY_TOP_K=8
POLICY_TOP_N=3
```

Restart the API. Until setup succeeds, `POLICY_MODE=local` preserves local policy
selection. Missing index/database/model or malformed results cause classified
local fallback. If the local policy is also unavailable, the existing error
remains. Model caches stay in the ignored directories configured by
`POLICY_MODEL_CACHE` and `POLICY_RERANKER_CACHE`.

`POLICY_INDEX_PATH` is accepted for old environment files but ignored. Seed
rebuilds from the canonical BRD section 9 records; it does not import Chroma data
or arbitrary PDFs. Current chunks represent complete policy rules. The embedding
model has a default input limit of 128 tokens and produces 384-dimensional
vectors; arbitrary long documents require tokenizer-aware ingestion before they
can be supported. Database storage capacity does not increase that model limit.

## Read the tables in DBeaver

Refresh `tera → Schemas → rag → Tables`:

- `policy_generations`: corpus/model fingerprint, model identity, dimensions and
  readiness. Different model generations stay isolated.
- `policy_chunks`: chunk ID, category, effective dates, policy text, provenance
  metadata and embedding. The current corpus has 15 chunks across five policies.

Repeat seed replaces one generation in a transaction, without duplicate IDs. A
failed reseed rolls back, preserving its previously committed data. Different
fingerprints remain stored; no automatic old-generation cleanup is implemented.
Search uses exact cosine distance after fingerprint/category/date filtering,
with a B-tree filter index. HNSW/IVFFlat are deferred until corpus scale and
benchmarks justify approximate search. Application shutdown disposes its pool.

## Testing and deployment

Routine unit/API tests inject fake embeddings, reranking and a memory vector
store. Set `TEST_POSTGRES_URL` to a local PostgreSQL connection with permission
to create disposable databases, then run `python -m pytest`. The PostgreSQL
fixture creates/drops only uniquely named test databases. Real pgvector cases
cover repeated seed, atomic rollback, category/date filters, model dimensions
and reopening from a separate process. Without the server extension those
cases explicitly skip; unit test success is not pgvector integration validation.
No tests download models or call the extraction provider. CI stays disabled.

On hosted PostgreSQL, confirm the provider supports pgvector and that its type
and operators are available in `public`. Preserve provider-required TLS options
in `DATABASE_URL`. Run seed with an administrative role; the RAG runtime needs
only schema usage and SELECT on its tables (the claim/checkpoint components have
their own write needs). Include `rag` in database backups. Backend hosting must
also have enough memory for the embedding/reranker models; storing vectors in
managed PostgreSQL does not run those models there.

## Historical native-server validation — 2026-10-09

Local backend verification: **365 passed, 5 skipped**. The five skipped tests
require pgvector, which is not yet installed on the native PostgreSQL 18 server.
The missing-extension rollback and request-without-index fallback tests passed
against isolated PostgreSQL databases. `pip check` passed. Real pgvector
seed/retrieval/benchmark validation remains pending installation. Earlier Chroma
model/benchmark results in the design document are historical, not evidence for
the replacement adapter.

References: [pgvector](https://github.com/pgvector/pgvector),
[embedding model architecture](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2#full-model-architecture).

## Docker validation — 2026-10-10

Docker Desktop was repaired using the official signed per-user installer and
WSL 2. Compose is healthy on **127.0.0.1:5434**; port 5433 belongs to the existing
prism-db project and is untouched. Runtime PostgreSQL is 18.6, vector extension
0.8.7. The image digest used was
`sha256:2358fcba361ed2233a5ed81b5fe4ca779ccb304120ce531a3bf51c0ed7e2bc11`.

Full local suite against isolated Docker PostgreSQL databases: **369 passed,
1 skipped** in 115.58 seconds. All five formerly blocked pgvector cases passed.
The missing-server-extension case skips because this server includes pgvector.
Cached real-model seed/verify/benchmark passed with HF_HUB_OFFLINE=1 and no
extraction API calls. All five policies match the canonical local policies.
Nine synthetic queries produced search top-1 4/9 and reranked top-1 7/9;
MRR@3 was 0.648 and 0.889. Mean warmed search was 62.65 ms, additional reranking
278.07 ms during this laptop run. These are evidence-relevance measurements,
not general accuracy guarantees. After restarting the container, all 15 chunks
remained in the volume. Local backend configuration now uses sql/rag/cross_encoder
on port 5434, with an ignored backup of prior settings and provider fields
preserved. No native database data was migrated or deleted.
