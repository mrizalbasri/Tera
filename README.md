<p align="center">
  <img src="frontend/static/logo.webp" alt="Logo Tera" width="120" />
</p>

# Tera

Tera adalah aplikasi reimbursement karyawan dengan agent untuk membaca nota,
memeriksa klaim terhadap kebijakan perusahaan, dan membantu tim keuangan
meninjau pengajuan. Kebutuhan bisnis tersedia di
[dokumen BRD](docs/BRD_Expense_Reimbursement_Agent.md).

## Masalah dan solusi

Pemeriksaan reimbursement manual mengharuskan tim keuangan membaca nota,
mencocokkan nominal, memeriksa kebijakan perusahaan, dan mencari klaim duplikat.
Informasi yang kurang jelas juga memerlukan klarifikasi dari karyawan.

Tera membantu memproses klaim dari unggahan nota: mengekstrak data, menjalankan
validasi dan evaluasi kebijakan, lalu mencatat keputusan beserta alasannya.
Klaim yang membutuhkan informasi tambahan masuk ke alur klarifikasi; klaim
yang memerlukan pertimbangan manusia masuk ke antrean review.

## Fitur utama dan target pengguna

| Pengguna | Kebutuhan dan fitur |
| --- | --- |
| Karyawan | Mengunggah nota, mengajukan klaim, melihat riwayat/status, dan menjawab klarifikasi |
| Tim keuangan / reviewer | Memeriksa bukti, temuan validasi, kebijakan, sinyal duplikasi/anomali, lalu menyetujui atau menolak dengan alasan |
| Admin | Mengakses antrean review dan laporan serta mengunduh CSV |

Pemrosesan menggunakan LangGraph dengan checkpoint untuk menunggu klarifikasi
atau review. Ekstraksi tersedia melalui provider mock atau model vision yang
mendukung endpoint OpenAI-compatible. Retrieval kebijakan dengan pgvector dan
skor anomali Isolation Forest dapat diaktifkan secara terpisah.
Login normal memakai Clerk; mode demo lokal tersedia tanpa akun.

## Tech stack dan arsitektur

![SvelteKit](https://img.shields.io/badge/SvelteKit-FF3E00?style=flat&logo=svelte&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langgraph&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat&logo=sqlalchemy&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikitlearn&logoColor=white)
![Clerk](https://img.shields.io/badge/Clerk-6C47FF?style=flat&logo=clerk&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat&logo=pytest&logoColor=white)
![Vitest](https://img.shields.io/badge/Vitest-6E9F18?style=flat&logo=vitest&logoColor=white)

| Bagian | Teknologi |
| --- | --- |
| Antarmuka | Svelte 5, SvelteKit, TypeScript, Vite |
| API dan kontrak | Python, FastAPI, Pydantic |
| Agent | LangChain, LangGraph, provider vision OpenAI-compatible |
| Penyimpanan | SQLAlchemy, PostgreSQL, checkpoint LangGraph; memory untuk demo |
| Kebijakan dan anomali | pgvector, SentenceTransformers, scikit-learn |
| Autentikasi | Clerk, verifikasi JWT di backend |
| Pengujian | pytest, Vitest, svelte-check |

Browser mengakses SvelteKit, yang meneruskan permintaan `/api` ke FastAPI.
Route API memanggil service untuk intake dan pemrosesan. Workflow menjalankan
ekstraksi, validasi, evaluasi kebijakan, deteksi duplikasi, skor anomali, dan
keputusan. Repository menyimpan klaim dan bukti; audit mencatat peristiwa
pemrosesan. Lihat [arsitektur sistem](docs/architecture/overview.md) dan
[alur agent](docs/architecture/agent-flow.md).

## Website, screenshot, dan dokumentasi

URL website live belum tercantum dalam dokumentasi repository. Untuk mencoba
secara lokal, buka [Tera lokal](http://localhost:5173) setelah menjalankan kedua
server di bawah. Dokumentasi API interaktif tersedia di
[Swagger UI lokal](http://127.0.0.1:8000/docs).

Tampilan workspace pengajuan klaim:

![Workspace pengajuan klaim Tera](docs/development/screenshots/tera-claim-workspace.png)

- [Indeks dokumentasi](docs/README.md)
- [Business requirements](docs/BRD_Expense_Reimbursement_Agent.md)
- [Login, akses pengguna, dan mode demo](docs/admin-login.md)
- [Operasional backend](docs/development/backend-operations.md)
- [Kontribusi dan validasi](CONTRIBUTING.md)

## Panduan tugas tim

Pembagian tugas Sheren dan Nisa, langkah onboarding, jadwal, dan kriteria
selesai ada di [README frontend](frontend/README.md). Keduanya menangani
frontend; pemilik proyek menangani backend.
Rencana ini disusun dari working tree lokal pada 14 Oktober 2026; beberapa
keterangan status fitur di bawah masih merujuk baseline sebelumnya. Pemilik
perlu membagikan baseline Git yang lengkap sebelum anggota mulai bekerja.

## Repository layout

```text
backend/   FastAPI API and agent services
frontend/  SvelteKit web interface
data/      Schemas and synthetic samples only
docs/      Architecture and project documentation
```

### Backend responsibilities

| Package | Responsibility |
| --- | --- |
| `app/agent/` | LangGraph workflow, thin nodes, control state, checkpoint runtime and prompt templates |
| `app/services/` | Claim processing lifecycle, extraction, validation, decisions, clarification and review |
| `app/integrations/` | LLM transport, outbound privacy controls, policy retrieval and other adapters |
| `app/domain/` and `app/schemas/` | Business states, transitions and typed data contracts |
| `app/repositories/` | Persistence contracts and implementations |
| `app/api/` and `app/audit/` | HTTP endpoints, dependency wiring and audit events |

`ClaimProcessingService` composes `ExtractionService` and the agent workflow.
Graph nodes call public service operations; business rules stay outside the
graph topology. Prompt instructions live in `app/agent/prompts/extraction.py`;
masking, image sanitization and multimodal message construction remain in
`app/integrations/llm_prompt.py` at the outbound privacy boundary.
See [the agent module guide](docs/architecture/agent-modules.md) for the dependency
flow and checkpoint compatibility constraints.

## Local setup

Siapkan Python beserta `venv`, Node.js yang kompatibel dengan Vite 8, dan pnpm
sesuai field `packageManager` di `frontend/package.json`. PostgreSQL diperlukan
untuk penyimpanan SQL; Docker diperlukan bila memakai `compose.yaml` untuk
pgvector. Mode demo memory tidak membutuhkan database atau API key.
Jalankan backend dan frontend pada dua terminal terpisah dari root repository.

### Environment variables

Salin `backend/.env.example` dan `frontend/.env.example` ke `.env` pada folder
masing-masing. Jangan menimpa `.env` lokal yang sudah dikonfigurasi.

| File | Variabel | Penggunaan |
| --- | --- | --- |
| Backend | `DEMO_MODE`, `ENVIRONMENT` | Untuk mencoba tanpa login, set `DEMO_MODE=true` dan `ENVIRONMENT=development`; demo memaksa memory, mock, kebijakan local, dan anomali rules |
| Backend | `FRONTEND_ORIGIN` | Origin frontend untuk pemeriksaan permintaan; default `http://localhost:5173` |
| Backend | `CLERK_ISSUER`, `CLERK_ADMIN_USER_IDS` | Mode normal: issuer Clerk yang cocok dengan frontend dan daftar user ID admin dipisahkan koma; daftar kosong tidak memberi akses admin |
| Frontend | `VITE_CLERK_PUBLISHABLE_KEY` | Mode normal: publishable key dari instance Clerk yang sama |
| Frontend | `BACKEND_URL` | Origin FastAPI, default `http://127.0.0.1:8000`; hanya digunakan server |
| Backend | `STORAGE_BACKEND`, `DATABASE_URL`, `GRAPH_CHECKPOINT_SCHEMA` | Pilih `memory` atau `sql`; mode SQL membutuhkan URL database dan schema checkpoint |
| Backend | `PROVIDER_MODE` | Default `mock`; pilih `live` untuk ekstraksi model vision |
| Backend | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Konfigurasi endpoint, model, dan kredensial untuk provider live |
| Backend | `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`, `PROVIDER_FALLBACK`, `LLM_IMAGE_PRIVACY_MODE` | Batas panggilan provider, fallback, dan pengiriman gambar |
| Backend | `POLICY_MODE`, `POLICY_RERANK_MODE` | Default `local` dan `none`; mode RAG/reranker membutuhkan seed model dan indeks |
| Backend | `ANOMALY_MODE`, `ANOMALY_MODEL_PATH` | Default `rules`; mode `ml` membutuhkan model hasil training lokal |

Nilai batas unggahan, confidence, retry pemrosesan, recovery, dan rate limit
tersedia di [contoh konfigurasi backend](backend/.env.example). Referensi
frontend ada di [contoh konfigurasi frontend](frontend/.env.example).
Restart server setelah perubahan konfigurasi. Gunakan data sintetis pada demo;
data memory hilang ketika backend direstart. Mode demo ditolak di production.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Untuk percobaan lokal tanpa Clerk, ubah DEMO_MODE=true di .env.
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Health check: `http://127.0.0.1:8000/health`.

For persistent local development, set these values in `backend/.env`:

```dotenv
STORAGE_BACKEND=sql
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@127.0.0.1:5432/tera
GRAPH_CHECKPOINT_SCHEMA=langgraph
```

Create the `tera` database on your PostgreSQL server first. DBeaver can manage
the same server; it is not required for the backend to run. Replace the password
placeholder locally and URL-encode special characters in connection credentials.
Do not commit `.env`.

SQLAlchemy creates missing domain tables when the SQL repositories are first
used. LangGraph creates its checkpoint tables in the separate `langgraph` schema
when processing is first used. The database account needs permissions to create
these tables/schema for initial setup. Domain data and checkpoints persist in
the same PostgreSQL database across server restarts. Application shutdown closes
the checkpoint connection and disposes the repository connection pool.

In DBeaver, refresh `tera → Schemas → public → Tables` for claim tables and
`tera → Schemas → langgraph → Tables` for checkpoints. Schema separation keeps
table names independent; it does not replace access permissions.

`STORAGE_BACKEND=memory` and `PROVIDER_MODE=mock` remain the example defaults.
Memory mode uses an in-memory checkpointer and loses data on restart. Provider
configuration is independent of storage: keep your existing `LLM_BASE_URL`,
`LLM_MODEL` and `LLM_API_KEY` when enabling PostgreSQL. An OpenAI-compatible endpoint
on localhost is supported. Use `PROVIDER_MODE=live` to call it; JSON mode remains
enabled. External tracing is not enabled by this project.

### Processing and human input

`ClaimProcessingService` runs extraction, validation, policy evaluation, duplicate
detection, anomaly scoring and decision nodes in order. Each claim ID is its
stable graph thread ID. Public endpoints and response shapes stay the same.

- Clarification and review finish the current processing run with
  `needs_clarification` or `escalated`, then pause at a checkpoint.
- A clarification answer creates a new run and processes the claim again with
  the stored answer. Repeating the answer returns the saved result.
- A reviewer decision creates a new run and applies the review without calling
  the model again. The earlier agent decision and evidence remain available.
  Repeating a completed review still returns HTTP 409.
- Existing completed claims replay from domain records. Older waiting claims
  without checkpoints are bootstrapped into the corresponding wait node.

Checkpoints contain record IDs, pipeline version and control state. Receipt
bytes, prompts, credentials and free-text answers remain outside graph state.
Restart/resume is supported while waiting for human input. Automatic recovery
after a process dies in the middle of a node is outside M7.5. Per-claim locks
serialize requests within one server process; use one worker until coordination
across workers is implemented. PostgreSQL storage alone does not make claim
operations safe across multiple backend workers.

SQLite repositories and `SqliteSaver` remain available for legacy databases and
compatibility tests. `GRAPH_CHECKPOINT_PATH` only applies to that legacy mode;
PostgreSQL uses `GRAPH_CHECKPOINT_SCHEMA`. Existing SQLite data is not copied to
PostgreSQL automatically; keep old files if their records are needed.

### Backend tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Tests use mock providers, isolated stores and settings that do not read the
local `.env`. Tests currently run locally; the GitHub backend workflow is
manually disabled at the owner's request. To run the PostgreSQL
integration cases locally, set that variable to a PostgreSQL connection URL for
a test-capable account before running pytest. The account must have `CREATEDB`:
each case creates a unique `tera_test_*` database and removes only that database
afterward. No tests write fixtures into the application's `tera` database.
Without this variable, PostgreSQL integration cases are skipped; memory and
SQLite compatibility tests still run.

### Frontend

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env
pnpm dev
```

The web interface is available at the URL printed by SvelteKit.

The frontend now connects to FastAPI through a same-origin `/api` proxy.
Copy `frontend/.env.example` to `frontend/.env` if the backend runs somewhere
other than `http://127.0.0.1:8000`, then set the server-only `BACKEND_URL`.
Restart the frontend after configuration changes. Run FastAPI separately.

The workspace and `/dashboard` share the same `/api` transport and contracts in
`src/lib/types/claim.ts`. Browser requests do not use `PUBLIC_API_BASE_URL`.
Dashboard claim rows link to the persisted claim detail page; the review queue
uses that page for evidence inspection, reviewer identity, reason and confirmation.
The dashboard aggregates persisted claims, and reports read backend data.
Processing time and token usage are measured when available; estimated time
savings remain labelled assumptions, not demonstrated business impact.

- `/`: landing page Tera.
- `/pengajuan`: upload receipts and submit a claim.
- `/riwayat`: view claim history and status for the signed-in user.
- `/claims/{claim_id}`: explicitly start/retry processing, inspect extraction,
  validation, policy evidence and timeline, answer clarification, or review an
  escalated claim with a reason and confirmation.
- `/reviews`: load the admin review queue.
- `/reports`: admin reports and CSV download.

Intake and processing are separate steps so processing failures do not require
resubmitting saved receipts. Retrying the unchanged upload form reuses its
idempotency key. In normal mode, Clerk sessions identify employees and reviewers;
admin access requires the backend allowlist. Demo mode bypasses login for local
synthetic data. See [the access guide](docs/admin-login.md).
Optional ML anomaly scoring is available
after explicit local training; see [the ML setup guide](docs/development/ml-anomaly.md).

## RAG policy retrieval (M7.6)

RAG code lives in `backend/app/integrations/rag/`, with separate modules:

| Module | Responsibility |
| --- | --- |
| `corpus.py` | Trusted versioned policy records and source references |
| `chunking.py` | One complete rule per chunk, stable IDs; summary for the no-rule category |
| `embeddings.py` | Pinned multilingual SentenceTransformer, local CPU |
| `index.py` | Trusted chunks, explicit seed and generation readiness |
| `vector_store.py` / `pgvector.py` | Storage contract and PostgreSQL vector persistence |
| `query.py` | Bounded canonical concepts from extracted items/vendor, participant count |
| `search.py` | Category/date filters, cosine top-k, trusted candidate validation |
| `reranker.py` | Optional pinned local cross-encoder, top-n and score validation |
| `retriever.py` | Shared adapter, orchestration, complete Policy and safe fallback |
| `benchmark.py` | Explicit synthetic relevance and warmed latency comparison |

Ingestion: policy documents → atomic rule chunks → embeddings → PostgreSQL/pgvector.
Processing: safe contextual query → filtered top-k search → optional rerank →
complete validated Policy → deterministic evaluation. Retrieved chunks are
evidence; every rule in the selected policy is still evaluated.
`backend/app/seed_policy.py` remains the CLI entry point.

For local development, use `compose.yaml` to run PostgreSQL + pgvector on
`127.0.0.1:5434`, with a persistent volume and ignored credentials. Native
PostgreSQL on 5432 remains separate. See [the pgvector setup guide](docs/development/pgvector.md)
for Docker startup, DBeaver and configuration. From `backend/`, seed the BRD
section 9 category policies explicitly:

```powershell
python -m app.seed_policy --verify
# Prepare both models, verify full-policy parity, and measure retrieval relevance:
python -m app.seed_policy --with-reranker --verify --benchmark
```

The seed command downloads the public multilingual embedding model at an
immutable revision and writes the policy-only pgvector index in `DATABASE_URL`. `--with-reranker`
also prepares `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` at a pinned revision.
`--benchmark` prepares that model and compares both retrieval stages on fixed
synthetic rule queries. Models run on CPU, with remote code disabled; reranking
uses safetensors. First-time seeding requires internet access, but no LLM API key.
With a complete cache, set `HF_HUB_OFFLINE=1` to verify entirely offline.

Set these in `.env` after verification:

```dotenv
POLICY_MODE=rag
POLICY_RERANK_MODE=cross_encoder
POLICY_TOP_K=8
POLICY_TOP_N=3
```

`POLICY_MODE=local` and `POLICY_RERANK_MODE=none` remain the defaults. Reranking
is optional because it adds model memory and inference latency; compare benchmark
results before enabling it. Both top-k and top-n must be in 1–50 and top-n must
not exceed top-k. There may be fewer candidates after category/date filtering.
`POLICY_INDEX_SCHEMA=rag` separates vector tables from claim tables and
`GRAPH_CHECKPOINT_SCHEMA`. `POLICY_MODEL_CACHE=./data/local/policy_model` and
`POLICY_RERANKER_CACHE=./data/local/policy_reranker` remain ignored local caches.
The legacy `POLICY_INDEX_PATH` setting is accepted but ignored; old Chroma indexes
are not migrated. Reseed the canonical corpus into PostgreSQL (15 atomic chunks).
Reseed after changing corpus, chunking or embedding model. Fingerprints isolate
model/corpus generations, including vector dimensions. Repeat seeds replace only
the same generation atomically; a failed seed leaves its previous committed data
intact. Old generations are retained. Stop the API before seeding and restart
it afterward. Application shutdown disposes the RAG connection pool.

Requests load cached model files only, never download or seed. Missing index,
missing model, retrieval/reranking errors or invalid candidates/scores fall back to the local
policy store and produce a `policy.retrieved` audit/timeline event with safe
provenance. If no local policy applies, the existing policy-unavailable behavior
remains. Retrieval selects complete validated policy records; deterministic
evaluation and decision precedence remain authoritative. Claims/checkpoints stay
in PostgreSQL; pgvector stores policy embeddings in a separate schema. API
requests perform reads only and never create schemas, tables or extensions.
Search uses exact cosine distance over category/date/fingerprint-filtered rows,
with a B-tree filter index. ANN indexes are deferred until corpus scale warrants
benchmarking them.

Query context recognizes canonical policy concepts such as alcohol, SPBU,
business-trip evidence, meals, hotel, toll/parking and receipts. Unrecognized
free text is excluded; missing context uses the fixed category description.
Receipt text, names, account numbers, email addresses, answers and queries never
enter the index or retrieval audit. Audit records contain validated policy/rule/
chunk IDs, model identities, candidate count, fingerprint and reason codes only.

Routine tests use an injected memory vector store with fake embeddings/reranking;
separate integration tests exercise disposable PostgreSQL databases with pgvector.
No model downloads or API access are needed. `--verify` checks all five categories
against full local policies, using cached-only runtime loaders. `--benchmark`
reports top-1, MRR at top-n, and mean warmed search/reranking latency. These measure
evidence relevance, not approval accuracy; the full-policy evaluator is unchanged.
The corpus preserves existing policy behavior, including limits evaluated per
claim; aggregation per day/night is not introduced in this PR. ML anomaly
scoring is implemented separately from RAG; see the ML setup guide below.

## ML anomaly scoring (M7.6)

`ANOMALY_MODE=rules` remains the default. From `backend/`, train explicitly with
`python -m app.train_anomaly --verify`. This generates synthetic history, trains
versioned Isolation Forests, evaluates separate synthetic cases and publishes
`data/local/anomaly/model.joblib` with a JSON evaluation report. Add
`--export-dataset data/local/anomaly/synthetic.jsonl` to inspect feature rows.
Set `ANOMALY_MODE=ml` after training and restart the API. Requests never train,
download models or modify a model artifact.

The existing scorer protocol, endpoints and decision precedence remain stable.
High anomaly scores can escalate to a reviewer; they never issue an approval.
Fewer than three comparable usable prior claims gives neutral zero. Missing or
invalid model artifacts and prediction failures fall back to rule scoring with
visible provenance. Signals store numeric features, component scores and detector
version; timeline entries expose score/source/version. Models and synthetic
exports are local ignored files. Only load joblib artifacts produced by the
trusted local training command. Synthetic metrics are not real-world fraud
accuracy. See [the full setup guide](docs/development/ml-anomaly.md).

## Documentation in Obsidian

Open the `docs/` directory as an Obsidian vault. Start at [`docs/README.md`](docs/README.md). Documents use Obsidian wikilinks and Mermaid diagrams so the relationships can be explored in Graph View.

## Team contribution rule

Every commit must use [Conventional Commits](https://www.conventionalcommits.org/). Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before creating a branch or commit.

## Data safety

Do not commit real receipts, personal information, API keys, or other secrets. Use synthetic or properly anonymized data only. Environment files are ignored; commit only `.env.example` files with placeholder values.

## Project status

M0–M6 and M7 are merged, including the PR #11 JSON prompt, image metadata and
provider logging privacy fixes. M7 provides LangChain vision extraction through
an OpenAI-compatible endpoint, bounded retry, fallback and an image privacy gate.
M7.5 adds LangGraph orchestration and PostgreSQL checkpoint persistence for
development and deployment, with memory and legacy SQLite compatibility.
`PROVIDER_MODE=mock` remains the default and needs no API key. M7.6's first PR
adds optional local RAG policy selection. The ML extension adds offline synthetic
training and optional Isolation Forest scoring. The current working tree also
includes Clerk access controls, a local demo mode, and reports/CSV;
see [the access guide](docs/admin-login.md) for their setup and limitations.
The agent-readiness extension adds Indonesian printed-amount parsing,
independent total checks, bounded clarification, persistent notifications,
published policy versions and separate active/waiting/token metrics. Policy
drafts use a typed rule editor, immutable publication and effective dates.
The offline evaluator runs 18 labelled synthetic scenarios through LangGraph;
the separate live verifier submits one synthetic receipt without mock fallback.

Node/container packaging, frontend CI and a disposable PostgreSQL dump/restore
verifier are included. See the [deployment guide](docs/development/agent-deployment.md),
[test plan](docs/development/agent-readiness-test-plan.md) and
[recorded validation](docs/development/agent-readiness-validation-2026-10-23.md).
The [24 October follow-up](docs/development/production-follow-through-2026-10-24.md)
records production configuration and authentication fixes, full regression
results, and the latest live-provider connection failure.
Public deployment, real-account browser verification and user acceptance sessions
remain explicit rollout steps; local test results do not establish production
accuracy, cost savings or completed reimbursement payments.
