# PostgreSQL + pgvector for policy retrieval

Tera stores claims in PostgreSQL, checkpoints in `langgraph`, and policy vectors
in `rag` (configurable with `POLICY_INDEX_SCHEMA`). pgvector is a **PostgreSQL
server extension**, not a Python embedding model. This replaces the Chroma
adapter in the modular RAG PR; existing local Chroma files are left untouched.

## Native Windows / PostgreSQL 18

The owner installs system prerequisites. Install Visual Studio Build Tools with
**Desktop development with C++**, including the MSVC x64 compiler and Windows SDK.
PostgreSQL must include its development headers/libraries. Docker is optional
and is not required for this native installation.

Open **x64 Native Tools Command Prompt for VS** as administrator. These commands
use CMD syntax, not PowerShell. Choose a directory for the source checkout first:

```bat
set "PGROOT=C:\Program Files\PostgreSQL\18"
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

Compile against the same PostgreSQL major version that runs the database.
Do not copy binaries built against PostgreSQL 16 into PostgreSQL 18. If a build
cannot find `postgres.h`, check the installed PostgreSQL headers and `PGROOT`.
If `nmake` is unavailable, use the developer command prompt after installing C++
Build Tools. Follow the [official Windows installation instructions](https://github.com/pgvector/pgvector#windows).

In DBeaver, connect to the **tera** database and check availability:

```sql
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name = 'vector';
```

There must be a result row. Enable the extension in this database using an
administrator/database role allowed to install extensions:

```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

The adapter currently requires the vector type and operators in **public**.
For an existing installation in another schema, have the database administrator
adapt that installation; `IF NOT EXISTS` does not relocate an extension.

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

## Migration validation — 2026-10-09

Local backend verification: **365 passed, 5 skipped**. The five skipped tests
require pgvector, which is not yet installed on the native PostgreSQL 18 server.
The missing-extension rollback and request-without-index fallback tests passed
against isolated PostgreSQL databases. `pip check` passed. Real pgvector
seed/retrieval/benchmark validation remains pending installation. Earlier Chroma
model/benchmark results in the design document are historical, not evidence for
the replacement adapter.

References: [pgvector](https://github.com/pgvector/pgvector),
[embedding model architecture](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2#full-model-architecture).
