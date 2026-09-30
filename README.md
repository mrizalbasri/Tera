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

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

The web interface is available at the URL printed by SvelteKit.

## Documentation in Obsidian

Open the `docs/` directory as an Obsidian vault. Start at [`docs/README.md`](docs/README.md). Documents use Obsidian wikilinks and Mermaid diagrams so the relationships can be explored in Graph View.

## Data safety

Do not commit real receipts, personal information, API keys, or other secrets. Use synthetic or properly anonymized data only. Environment files are ignored; commit only `.env.example` files with placeholder values.

## Project status

The repository foundation is ready. OCR, policy retrieval, anomaly detection, persistence, and external LLM integration are planned in later changes.
