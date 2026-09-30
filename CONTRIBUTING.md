# Contributing

## Branches

Keep `main` stable. Create a focused branch for each change:

- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`

## Pull requests

Open a pull request for every change. Include the motivation, validation steps, and any data or security impact. Do not merge changes that contain secrets, real personal data, `venv`, `.venv`, or `node_modules`.

## Commits

Use Conventional Commits:

```text
feat(backend): add claim schema
fix(frontend): show upload error
docs: update setup guide
```

## Local checks

Backend:

```powershell
cd backend
python -m pytest
```

Frontend:

```powershell
cd frontend
pnpm check
pnpm build
```
