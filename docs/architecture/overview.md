# Architecture Overview

The prototype is a monorepo with a SvelteKit frontend and a FastAPI backend.

```mermaid
flowchart LR
    User[Employee or reviewer] --> Frontend[SvelteKit frontend]
    Frontend --> API[FastAPI API]
    API --> Agent[Agent orchestration]
    Agent --> Tools[Validation and policy tools]
    Agent --> Storage[(Claim storage)]
```

The current implementation contains only the API health check and frontend foundation. The remaining components are introduced incrementally.

Related documents:

- [[../README|Documentation index]]
- [[agent-flow|Agent flow]]
- [[../decisions/0001-monorepo|Monorepo decision]]
