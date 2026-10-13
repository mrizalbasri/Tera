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

The backend implements claim intake, extraction, validation, policy evaluation,
duplicate detection, rule-based anomaly scoring, decisions and human clarification
or review. LangGraph coordinates the processing steps; repositories store domain
records and a separate checkpoint runtime supports waiting-state resume.

See [[agent-modules|Agent module boundaries]] for the current source layout,
dependency flow and checkpoint compatibility constraints.

Related documents:

- [[../README|Documentation index]]
- [[agent-flow|Agent flow]]
- [[../decisions/0001-monorepo|Monorepo decision]]
