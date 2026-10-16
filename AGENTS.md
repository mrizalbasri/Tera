# Repository Guidelines

## Project Structure & Module Organization

Expense Agent uses a Python/FastAPI backend and SvelteKit/TypeScript frontend.

- `backend/app/`: API routes in `api/`, business logic in `services/`, domain states in `domain/`, typed contracts in `schemas/`, persistence in `repositories/`, provider adapters in `integrations/`, and audit events in `audit/`.
- `backend/tests/`: pytest suites and shared fixtures in `conftest.py`.
- `frontend/src/routes/`: SvelteKit pages and layouts; `src/lib/` holds shared code and bundled assets. `frontend/static/` holds public assets.
- `data/`: schemas and synthetic samples. `docs/`: requirements, architecture, decisions, and diagrams; open it as an Obsidian vault starting at `docs/README.md`.

## Build, Test, and Development Commands

Run backend commands from `backend/`, using an activated virtual environment:

- `python -m pip install -r requirements.txt`: install application and test dependencies.
- `Copy-Item .env.example .env`: create local configuration in PowerShell.
- `uvicorn app.main:app --reload`: start the API on port 8000.
- `python -m pytest`: run the backend suite.

Run frontend commands from `frontend/`:

- `pnpm install`: install dependencies.
- `pnpm dev`: start the development server.
- `pnpm check`: run Svelte and TypeScript checks.
- `pnpm build`: build for production; `pnpm preview` serves it.

## Coding Style & Naming Conventions

Follow existing files: Python uses four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and type annotations. Svelte/TypeScript uses tabs; retain SvelteKit names such as `+page.svelte` and `+layout.svelte`. Keep route handlers thin and business rules in services. No dedicated formatter or lint script is currently configured.

## Testing Guidelines

Use pytest and FastAPI `TestClient`. Name files `test_*.py` and functions `test_<behavior>`. Add regression coverage for changed behavior, including failure paths; use synthetic fixtures and isolated storage. No numeric coverage threshold or frontend test runner is configured. Run backend tests and frontend checks/build before submitting applicable changes.

## Commit & Pull Request Guidelines

Read `CONTRIBUTING.md` before branching or committing. History follows Conventional Commits, for example `fix(backend): validate receipt images`. Use a lowercase imperative description of at most 72 characters. Open a focused PR describing motivation, validation, and data/security impact; link relevant issues and include screenshots for visible UI changes.

- Name branches with the repository's semantic prefixes: `feat/`, `fix/`, or `docs/`; use the corresponding Conventional Commit type for other work. Never use `codex/` or any assistant/product name as a branch prefix.
- Use the user's configured Git identity for both commit author and committer. Verify the identity before committing; do not add `Co-authored-by` trailers or agent attribution to commit messages.
- Use shell Git for commits and pushes, and the authenticated `gh` CLI for GitHub mutations, including creating or editing PRs, comments, issues, and merges. Do not use the ChatGPT Codex Connector for these mutations, to avoid connector attribution on GitHub.
- If Git or `gh` is unavailable or authentication fails, report the blocker before switching to a connector. Existing PR attribution may remain; recreate a PR only when the user requests it.

## Security & Agent Guidance

Commit synthetic or anonymized data and placeholder `.env.example` values only. Keep receipts, personal information, credentials, and local environment files out of Git. Default `PROVIDER_MODE=mock` needs no API key.

When `.codegraph/` exists, use `codegraph_explore` or `codegraph explore "<symbol or question>"` before text searches or file reads to locate or understand code. Skip CodeGraph when that directory is absent.
