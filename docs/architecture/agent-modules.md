# Agent module boundaries

Tera separates graph orchestration from claim business operations. The
application entry point remains `ClaimProcessingService` in
`backend/app/services/processing.py`; API routes, clarification and review call
that service to start or resume work.

## Module map

| Module | Owns |
| --- | --- |
| `agent/workflow.py` | Graph construction, stable node names and routing |
| `agent/nodes.py` | Thin adapters from graph steps to public service operations |
| `agent/state.py` | Control-only `ClaimGraphState` and invocation-local `ReviewExecution` |
| `agent/runtime.py` | Checkpoint connections, shared per-claim locks, registry and shutdown |
| `agent/prompts/extraction.py` | Provider-independent receipt extraction instructions |
| `services/processing.py` | Processing runs, idempotency, replay and human-input resume |
| `services/extraction.py` | Persisted pipeline operations and evidence assembly |
| `services/validation.py`, `services/decision.py` | Deterministic validation and decision rules |
| `integrations/llm.py`, `integrations/llm_prompt.py` | Provider calls and outbound privacy enforcement |

`ClaimProcessingService` receives claim/run repositories, an `ExtractionService`
instance and shared graph resources explicitly. It does not inherit extraction
behavior. Dependency construction belongs to `api/deps.py`.

```text
API / clarification / review
    -> ClaimProcessingService
        -> workflow -> nodes -> public ExtractionService operations
        -> checkpoint runtime
        -> ExtractionService replay and claim transition operations

ExtractionService -> business services / adapters / repositories / audit
LLM adapter -> prompt template + outbound masking and image sanitization
```

Nodes orchestrate operations; they do not implement policy rules or use private
service methods. Validation and policy steps load persisted evidence through
`validate_claim` and `evaluate_claim_policy`. Prompt templates contain instructions
only; the provider adapter applies privacy gates before constructing outbound
messages. The agent package initializer intentionally imports no runtime modules,
so importing a prompt does not initialize a graph or checkpoint connection.

## Compatibility and failure behavior

The modularization preserves pipeline version `0.2.0`, graph node names, routing,
thread IDs, state fields and interrupt/resume payloads. Waiting checkpoints keep
working without a data migration. State contains only `claim_id`, `run_id`,
`pipeline_version` and `stage`; receipts, free-text answers, prompts and credentials
stay outside checkpoints. Review callbacks and results remain invocation-local.

Provider errors, confidence retries, policy fallback, failure recording, replay
and duplicate-request behavior retain their existing semantics. SQL nodes commit
their domain writes and completion marker together. Recovery replays completed
markers and resumes unfinished nodes. PostgreSQL advisory locks coordinate claim
mutations across workers; SQLite remains a single-process development option.
An automatic SQL recovery worker scans pending runs every 30 seconds by default.
Interrupted admin reviews require fresh authenticated input if the decision
transaction did not commit. See [[../development/backend-operations|Backend operations]].

## Verification

Run `.venv/Scripts/python.exe -m pytest` from `backend/` (or the equivalent
activated interpreter). The graph suite covers memory and SQLite persistence,
restart/resume, concurrent clarification/review, legacy claims without checkpoints,
privacy of checkpoint history and replay. PostgreSQL cases require an explicit
`TEST_POSTGRES_URL` and use disposable test databases. Provider privacy tests cover
the separately retained masking and image-sanitization boundary.

Related: [[overview|Architecture overview]], [[agent-flow|Agent flow]],
[[../README|Documentation index]].
