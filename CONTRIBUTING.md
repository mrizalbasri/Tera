# Contributing

## Branches

Keep `main` stable. Create a focused branch for each change:

- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`

## Pull requests

Open a pull request for every change. Include the motivation, validation steps, and any data or security impact. Do not merge changes that contain secrets, real personal data, `venv`, `.venv`, or `node_modules`.

## Commits

Every commit in this repository **must** follow the Conventional Commits format:

```text
<type>(<optional-scope>): <imperative description>
```

The description must be lowercase, imperative, and no longer than 72 characters.

Allowed types:

- `feat`: add a user-facing feature
- `fix`: fix a bug
- `docs`: change documentation only
- `refactor`: change code without changing behavior
- `test`: add or update tests
- `build`: change dependencies or build configuration
- `ci`: change continuous integration configuration
- `chore`: make maintenance or repository changes
- `perf`: improve performance
- `revert`: revert an earlier commit

Examples:

```text
feat(backend): add claim schema
fix(frontend): show upload error
docs: update setup guide
```

Do not use non-descriptive messages such as `update`, `changes`, or `final`. If a change introduces an incompatible public behavior, include a `BREAKING CHANGE:` footer in the commit body.

Before pushing, verify the commit message:

```powershell
git log -1 --format=%s
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
