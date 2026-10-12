# Agent module structure

## Approved scope

Separate existing agent orchestration, state, runtime and prompt instructions from
business operations. Replace processing/extraction inheritance with explicit
dependencies. Preserve public HTTP contracts and processing behavior. Do not add
unused tools, memory modules, model providers or new framework dependencies.

## Design

`agent/workflow.py` builds the existing graph using `ClaimNodes` from `nodes.py`.
`state.py` owns checkpoint control fields and request-local review context.
`runtime.py` owns shared checkpoint resources and claim locks. Prompt instructions
move to `agent/prompts/extraction.py`, while the outbound privacy adapter stays in
`integrations/llm_prompt.py`.

`ClaimProcessingService` composes `ExtractionService`, claim/run repositories and
graph resources. Extraction exposes public validation, policy evaluation, replay,
transition and run-completion operations for orchestration. Existing validation,
decision, provider and repository implementations retain their behavior.

## Implementation sequence

1. Record the existing backend test baseline.
2. Extract state, runtime, topology, nodes and prompt instructions.
3. Replace inheritance with composition and update dependency wiring/imports.
4. Document responsibilities and compatibility constraints.
5. Run the backend suite, check old waiting-checkpoint resume against the new
   workflow, and inspect the final diff.

## Acceptance criteria

- API, clarification and review continue to use the processing service.
- Nodes call public business operations without embedding policy rules.
- Node names, state keys, pipeline version, thread IDs and resume payloads remain
  stable; no checkpoint migration is required.
- Provider privacy gates, fallback, retries, decisions and audit behavior remain
  covered by the existing regression suites.
- No secrets, real receipts, environment files or local model data are added.

See [[../../architecture/agent-modules|Agent module boundaries]] for the final map.
