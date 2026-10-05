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
  decide -> needs_clarification  -> INTERRUPT (employee answer)
  decide -> escalated            -> INTERRUPT (reviewer decision)
  decide -> approved | rejected  -> END
```

- Conditional edges mirror the FR-08 precedence exactly; the graph does not
  add, reorder, or soften precedence.
- Clarification and review resume via `interrupt()` + `Command(resume=...)`
  with the LangGraph checkpointer (SQLite), keyed by claim id.
- A resumed run still creates a NEW ProcessingRun; graph checkpoints
  complement, never replace, ProcessingRun/AuditEvent persistence.

## Guardrails

- Masking (FR-13) runs before any node touches an external provider.
- The checkpointer stores state without raw receipt bytes; audit payloads stay
  safe (M6 rules).
- Every node wraps an existing service; no business logic moves into the
  graph definition.

## Interfaces

- `ClaimProcessingService.process_claim` becomes the graph entry point; the
  HTTP contract (`POST /claims/{id}/process`, idempotency keys, clarifications,
  reviews) is unchanged.
- Checkpointer database path from settings; `PROVIDER_MODE` unchanged from M7.

## Acceptance criteria

- All 85+ existing tests pass unchanged in behaviour (status transitions,
  precedence, idempotency, replay semantics).
- Interrupt/resume reproduces the shared-meal and review journeys end-to-end.
- Timeline (FR-12) gains no duplicate events from graph mechanics.

## Tests

Existing suite must stay green; add: interrupted-graph resume per scenario
( clarified claim, escalated claim), checkpoint survival across restart, and
a property test that graph outcome equals the non-graph pipeline for the same
fixtures.

## Dependencies

`langgraph` (pinned), LangChain stack from M7.
