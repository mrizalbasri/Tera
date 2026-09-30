# Expense Agent Repository Setup Design

## Status

Approved design for the initial team repository foundation.

## Goal

Prepare `mrizalbasri/Tera` as a safe, documented, and collaborative monorepo for the Expense Reimbursement Agent prototype before feature development begins.

The initial setup must support:

- FastAPI and Python for the backend.
- SvelteKit and TypeScript for the frontend.
- Markdown documentation that can be opened as an Obsidian vault.
- Public-repository safety for a competition project.
- A predictable team workflow led through pull requests.

The initial setup does not implement OCR, RAG, anomaly detection, database persistence, or LLM integration.

## Repository Structure

```text
Tera/
├─ backend/
│  ├─ app/                 # API, agent, domain, tools, persistence
│  ├─ tests/
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  ├─ static/
│  ├─ tests/
│  ├─ package.json
│  └─ .env.example
├─ data/
│  ├─ schemas/
│  └─ samples/             # synthetic or anonymized data only
├─ docs/
│  ├─ README.md
│  ├─ architecture/
│  ├─ decisions/
│  └─ policies/
├─ BRD_Expense_Reimbursement_Agent.md
├─ README.md
├─ CONTRIBUTING.md
├─ .gitignore
└─ .github/
   ├─ ISSUE_TEMPLATE/
   ├─ pull_request_template.md
   └─ CODEOWNERS
```

The root `README.md` is the GitHub onboarding page. `docs/README.md` is the documentation-vault index for Obsidian. They serve different audiences and both remain in the repository.

## Dependency and Environment Policy

The repository must never contain local environments or installed dependencies:

- Python contributors create a local `.venv/`; `.venv/` is ignored.
- Backend dependencies are committed in `backend/requirements.txt`.
- Frontend dependencies are committed in `frontend/package.json` and its package-manager lockfile.
- `node_modules/`, build output, caches, local databases, and environment files are ignored.
- `.env.example` files contain variable names and dummy placeholders only.
- Real API keys, tokens, private keys, and personal data must not be committed.

`requirements.txt` is intentionally used for the first scaffold because it is straightforward for all contributors. The project can move to `pyproject.toml` later when packaging or tooling needs justify it.

## Obsidian Documentation

The `docs/` directory is a Markdown vault that can be opened directly in Obsidian.

Documentation relationships use Obsidian wikilinks, for example:

```markdown
[[BRD_Expense_Reimbursement_Agent]]
[[architecture/agent-flow]]
[[decisions/0001-monorepo]]
```

Architecture diagrams may use Mermaid. Obsidian will show relationships in Graph View when documents link to one another.

Personal Obsidian workspace state must not be committed. Only shared configuration that is deliberately needed by the team may be added later.

## Team Workflow

- `main` is the stable branch.
- Work uses `feat/...`, `fix/...`, or `docs/...` branches.
- Changes merge through pull requests.
- At least one review is required before merging.
- `main` should be protected against direct pushes and force-pushes.
- CODEOWNERS identifies the repository lead or designated maintainers for critical areas.
- Commit messages follow Conventional Commits.
- Issue templates cover features, bugs, and documentation tasks.
- The pull request template requires a summary, validation steps, data-safety check, and secret check.

## Data and Security Guardrails

The public repository may contain only synthetic data or data whose license and attribution are clear.

- Real receipts must be anonymized before use.
- Personal identifiers must not be stored in samples.
- Dataset licenses and attribution must be documented.
- Agent secrets must be supplied through local environment variables or GitHub Secrets.
- The repository should enable secret scanning and push protection when available.

## Initial Validation

The foundation setup is complete when:

1. The local Git repository is connected to `git@github.com:mrizalbasri/Tera.git`.
2. The backend can be installed from `backend/requirements.txt` and exposes a health-check endpoint.
3. The frontend can install from its lockfile and start a SvelteKit development server.
4. README files explain setup, environment variables, data rules, and the Obsidian documentation layout.
5. `git status` contains no `.venv/`, `node_modules/`, secrets, or personal data.
6. The initial commit contains only repository foundation and scaffold files.

## Out of Scope

The following are intentionally deferred:

- Full authentication and authorization.
- OCR and receipt preprocessing.
- Policy RAG.
- Duplicate and anomaly detection.
- Production database schema.
- External LLM integration.
- Accounting, WhatsApp, email, or multi-level approval integrations.
- CI checks that depend on final framework tooling.

