# ADR 0001: Use a Monorepo

## Decision

Keep the FastAPI backend, SvelteKit frontend, shared documentation, and safe test data in one repository.

## Rationale

The competition prototype is developed by one team and needs synchronized requirements, UI, API, and documentation. A monorepo makes onboarding and pull-request review straightforward while keeping the initial architecture visible.

## Consequences

- Backend and frontend retain independent dependency manifests.
- Team members can work in focused branches and directories.
- Deployment can be split later without changing the product documentation layout.

Related documents:

- [[../README|Documentation index]]
- [[../architecture/overview|Architecture overview]]
