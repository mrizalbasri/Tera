# ADR 0002: Adopt LangChain, LangGraph, RAG, and ML anomaly scoring

## Decision

Adopt four technology additions for the Expense Agent backend, staged across
milestones M7, M7.5, and M7.6:

1. **LangChain** (`langchain`, `langchain-openai`) as the LLM model layer for
   receipt extraction, pointed at an OpenAI-compatible endpoint (GLM vision
   via Z.ai) and selected by `PROVIDER_MODE=mock|live`.
2. **LangGraph** as the claim-processing pipeline orchestrator, modelling the
   existing deterministic flow (extract → validate → policy → duplicate →
   anomaly → decide) as an explicit graph with **interrupts** for employee
   clarification (FR-09) and human review (FR-10).
3. **RAG policy retrieval** (`chromadb` + multilingual
   `sentence-transformers` embeddings) behind the existing `PolicyRetriever`
   protocol, upgrading the local versioned policy store of M3 (FR-05).
4. **ML anomaly scoring** (`scikit-learn` Isolation Forest over synthetic
   claim history) behind the existing `AnomalyScorer` protocol, upgrading the
   rule-based scorer of M4 (FR-07).

## Rationale

- The GTNIC judging criteria reward agent autonomy, reasoning, and an
  innovation claim the BRD already makes: RAG-based policy compliance plus ML
  anomaly detection. These additions make that claim real.
- `PolicyRetriever` and `AnomalyScorer` protocols were introduced in M0
  precisely so implementations could be swapped incrementally; these upgrades
  change no pipeline code.
- LangGraph interrupts map directly onto the clarification and review flows
  already implemented, with a checkpointer that complements (not replaces)
  ProcessingRun and AuditEvent persistence.
- LangChain's structured-output support keeps provider output flowing through
  the existing Pydantic validation boundary.

## Non-negotiable guardrails

- `SensitiveDataMasker` runs in our code before any content reaches a
  LangChain model; no exception (FR-13).
- Deterministic validation and the decision engine's conservative precedence
  remain authoritative — the LLM never sets a final outcome (FR-08, M7 rule).
- All provider calls stay behind existing protocols; tests always run against
  deterministic mocks.
- Every added dependency is version-pinned in `requirements.txt` and ships
  with its own tests.

## Consequences

- `requirements.txt` grows (langchain, langchain-openai, langgraph, chromadb,
  sentence-transformers, scikit-learn) — pinned per milestone.
- Demo and tests can run fully deterministic with `PROVIDER_MODE=mock`; live
  mode requires an API key in `.env` only.
- The `integrations/` boundary remains the only place that knows about these
  libraries.

## Status

Accepted, 2026-10-05.

Related documents:

- [[../README|Documentation index]]
- [[0001-monorepo|ADR 0001: Monorepo]]
- [[../superpowers/specs/2026-10-01-expense-agent-backend-m7-privacy-integrations-spec|M7 spec (tooling addendum)]]
- [[../superpowers/specs/2026-10-05-expense-agent-backend-m75-langgraph-orchestration-spec|M7.5 spec]]
- [[../superpowers/specs/2026-10-05-expense-agent-backend-m76-rag-policy-ml-anomaly-spec|M7.6 spec]]
