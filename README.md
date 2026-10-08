# Expense Agent

Expense Agent is a prototype AI agent for processing employee expense reimbursement claims. The business requirements are documented in [`docs/BRD_Expense_Reimbursement_Agent.md`](docs/BRD_Expense_Reimbursement_Agent.md).

This repository uses:

- **Backend:** FastAPI and Python
- **Frontend:** SvelteKit and TypeScript
- **Documentation:** Markdown designed to work as an Obsidian vault

## Repository layout

```text
backend/   FastAPI API and agent services
frontend/  SvelteKit web interface
data/      Schemas and synthetic samples only
docs/      Architecture and project documentation
```

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
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
local `.env`. GitHub CI runs the same suite without provider credentials.
CI starts PostgreSQL 18 and sets `TEST_POSTGRES_URL`. To run the PostgreSQL
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
pnpm dev
```

The web interface is available at the URL printed by SvelteKit.

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
`PROVIDER_MODE=mock` remains the default and needs no API key. Still planned:
RAG policy retrieval and ML anomaly scoring (M7.6), and reporting/export (M8).
OCR, frontend work and the large-number validation bug tracked in
[issue #12](https://github.com/mrizalbasri/Tera/issues/12) are outside M7.5.
