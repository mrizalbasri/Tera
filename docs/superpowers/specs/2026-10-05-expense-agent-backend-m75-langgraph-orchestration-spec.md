# Backend M7.5 — LangGraph Pipeline Orchestration Spec

## Purpose

Re-express the claim-processing pipeline as a LangGraph graph so the agent
flow becomes explicit, checkpointed, and interruptible — without changing any
outcome. Deterministic behaviour of M3–M6 is preserved exactly.

## FR coverage

FR-09 (clarification conversation), FR-10 (human escalation), FR-12 (agent
step trace) — plus FR-02/03/04/05/06/07/08 as graph nodes that already exist.

## Graph design

```text
START
  -> extract            (ReceiptExtractor; masked input in live mode)
  -> validate           (ValidationService -> ValidationFinding)
  -> evaluate_policy    (PolicyRetriever + PolicyEvaluator -> PolicyEvaluation)
  -> detect_duplicates  (DuplicateDetector -> Signal)
  -> score_anomaly      (AnomalyScorer -> Signal)
  -> decide             (DecisionEngine; conservative precedence, unchanged)
  extract -> low confidence     -> wait_clarification -> INTERRUPT
  decide -> needs_clarification -> wait_clarification -> INTERRUPT
  decide -> escalated           -> wait_review        -> INTERRUPT
  decide -> approved | rejected  -> END

  resume clarification -> new ProcessingRun -> extract
  resume review        -> new ProcessingRun -> apply_review -> END
```

- Conditional edges mirror the FR-08 precedence exactly; the graph does not
  add, reorder, or soften precedence.
- Clarification and review resume via `interrupt()` + `Command(resume=...)`
  with the LangGraph checkpointer (SQLite), keyed by claim id.
- A resumed run still creates a NEW ProcessingRun; graph checkpoints
  complement, never replace, ProcessingRun/AuditEvent persistence.
- Decision persistence, clarification creation and review creation happen
  before entering the dedicated wait node. Wait nodes only interrupt and
  return the resumed run ID, since LangGraph re-executes them on resume.
- Review resumes directly into the existing review service. It saves a new
  reviewer decision, retaining the agent decision and evidence references,
  without invoking extraction or other provider nodes again.

## Guardrails

- Masking (FR-13) runs before any node touches an external provider.
- Graph state stores only `claim_id`, `run_id`, `pipeline_version` and `stage`.
  LangGraph checkpoint metadata/pending writes contain control data and IDs.
  Images, prompts, API keys and free-text answers never enter state or resume
  payloads. Domain repositories retain the records needed by each node.
- Review callbacks/results use invocation-local runtime context, which is not
  checkpointed. External tracing is not enabled automatically.
- Every node wraps an existing service; no business logic moves into the
  graph definition.
- Extraction retry/fallback/privacy rules remain in the existing components;
  the graph adds no retry policy.

## Interfaces

- `ClaimProcessingService.process_claim` becomes the graph entry point; the
  HTTP contract (`POST /claims/{id}/process`, idempotency keys, clarifications,
  reviews) is unchanged.
- Internal `resume_clarification` and `resume_review` use `Command(resume=...)`
  with a new run ID. The public endpoint/request/response contracts are unchanged.
- An answered clarification replays the recorded result; an already decided
  review is still rejected with HTTP 409.
- Shared per-claim locks serialize processing, answer and review operations
  within one process, including across request-scoped service instances.
  Repository idempotency reservations remain in place.

## Local persistence and compatibility

- `STORAGE_BACKEND=memory`: memory domain repositories plus `InMemorySaver`.
- `STORAGE_BACKEND=sql`: SQL repositories plus `SqliteSaver` in a separate file.
  `DATABASE_URL=sqlite:///./expense_agent.db` stores domain data;
  `GRAPH_CHECKPOINT_PATH=./expense_agent_checkpoints.db` stores checkpoints.
- Paths are relative to the server working directory. Use `backend/` consistently
  and keep both files when restarting. Saver resources are shared per repository
  bundle, opened lazily and closed by the FastAPI lifespan at shutdown.
- Local development uses SQL storage while the example and isolated tests keep
  memory/mock defaults. Provider/model/key settings are independent of storage.
- Completed M7 claims replay from stored domain records. Waiting M7 claims with
  no checkpoint bootstrap a wait checkpoint from their prior terminal run before
  resuming. This creates no duplicate decisions, clarifications or audits.
- Supported recovery is restart while waiting for human input. Automatic
  recovery from a crash halfway through a node and multiple worker coordination
  are outside M7.5; use one server worker for local development.
- SQLite database and WAL/SHM/journal files stay out of Git.

## Acceptance criteria

- All 138 existing tests pass unchanged in behaviour (status transitions,
  precedence, idempotency, replay semantics).
- A review now records a new processing run as specified above.
- Interrupt/resume reproduces the shared-meal and review journeys end-to-end.
- Timeline (FR-12) gains no duplicate events from graph mechanics.
- Checkpoint history contains no raw receipt, prompt, credential or free text.

## Tests

Run the original behavioural suite and `tests/test_m75_graph.py` with mocks.
The graph tests cover memory and SQLite routing, low confidence, classified
failures, clarification/review resume, restart, old waiting claims, duplicate
requests, concurrent answers/reviews, isolation between claims and checkpoint
privacy. Existing decision/fallback tests continue to verify rejected outcomes,
conservative precedence and degraded providers. Tests disable local dotenv reads.

Run a separate synthetic image smoke test against the developer's configured
OpenAI-compatible endpoint after upgrading dependencies. It must use no fallback;
credentials and personal receipts are never part of CI or committed fixtures.

## Dependencies

```text
langchain==1.4.3
langchain-core==1.6.7
langchain-openai==1.6.7
langgraph==1.2.14
langgraph-checkpoint==4.2.0
langgraph-checkpoint-sqlite==3.1.1
```

JSON mode and the OpenAI-compatible adapter remain in use. M7 is merged in
PR #11. OCR, RAG, ML anomaly, frontend changes and P2 issue #12 remain outside
this milestone.

Implementation follows the upstream [interrupt rules](https://docs.langchain.com/oss/python/langgraph/interrupts)
and [runtime context API](https://docs.langchain.com/oss/python/langgraph/graph-api#runtime-context).
