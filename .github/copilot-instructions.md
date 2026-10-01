# Copilot instructions for Tera

## Project overview

This repository is a monorepo for an Expense Agent prototype. The architecture is intentionally split into a FastAPI backend and a SvelteKit frontend, with product and architectural documents kept in `docs/`.

- `backend/`: FastAPI service, settings, and tests
- `frontend/`: SvelteKit + TypeScript UI
- `docs/`: BRD, architecture notes, and decision records
- `data/`: synthetic/safe sample data only

The current codebase is still a foundation: the backend exposes a basic `/health` endpoint and the frontend has the starter SvelteKit app. Treat new work as incremental additions to this structure rather than a single full-stack app with hidden conventions.

## Setup and validation commands

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest
```

Run one backend test directly:

```powershell
cd backend
python -m pytest tests/test_health.py -q
```

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

Run the repo's validation checks:

```powershell
cd frontend
pnpm check
pnpm build
```

There is no dedicated `lint` script in `frontend/package.json`; `pnpm check` is the project’s main static validation step and `pnpm build` is the production verification pass.

## Architecture notes

### Backend

The backend entry point is `backend/app/main.py`. It creates the FastAPI app, configures CORS against the frontend origin, and exposes `/health`.

Configuration lives in `backend/app/config.py` and uses `pydantic-settings` with environment variables from `.env` via `BaseSettings`. This is the place to add new app-wide settings and env-driven configuration.

### Frontend

The frontend is a SvelteKit app using TypeScript and Vite. The main app structure lives under `frontend/src/` and routes are defined in `src/routes/`. Keep route-level code simple and feature-specific; the app is still early-stage and not yet organized into a deeply layered frontend architecture.

### Documentation and decision-making

`docs/` is meant to be opened as an Obsidian vault. Start from `docs/README.md` and follow the architecture and decision docs when you need product context or intent. The repo intentionally keeps product requirements, architecture, and decisions alongside code so PRs can be understood without tracing multiple separate systems.

## Repo-specific conventions

- Commit messages must follow Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, `revert`).
- Never add a `Co-authored-by: Copilot` trailer or any Copilot attribution to commit messages unless explicitly requested by the user.
- Keep `main` stable and work from focused branches like `feat/<short-description>` or `fix/<short-description>`.
- Open a PR for each change and include motivation, validation, and any security/data impact.
- Do not commit secrets, API keys, receipts, or personal data. Use the synthetic data model and placeholder values only.
- Environment files are local-only; commit only sanitized examples such as `.env.example`.
- The repo is intentionally a monorepo with independent backend/frontend dependency manifests; prefer feature work that matches each side’s existing boundary instead of introducing extra top-level tooling.

## Working style for this repo

When adding code or docs, prefer changes that align with the existing structure:

- backend changes stay under `backend/app/` and tests in `backend/tests/`
- frontend changes stay under `frontend/src/` and route-level additions remain SvelteKit-native
- documentation updates belong in `docs/` and should preserve the existing Obsidian linking style when relevant

This repo is small enough that the code and design intent are still tightly coupled; read the docs and adjacent files before designing new abstractions or cross-cutting patterns.
