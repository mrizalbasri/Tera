# Backend M7.6 — RAG Policy Retrieval and ML Anomaly Scoring Spec

## Purpose

Delivery is split into two PRs: RAG policy selection first, ML anomaly scoring
second. M7.5 is merged; PostgreSQL remains the domain/checkpoint backend.

Upgrade two provider implementations behind existing protocols — turning the
BRD's innovation claim ("kepatuhan kebijakan (RAG), deteksi anomali (ML)")
into working software, without touching pipeline or decision logic.

## FR coverage

FR-05 (policy retrieval via RAG) and FR-07 (anomaly scoring with ML).

## Part 1 — RAG policy retrieval (FR-05)

- New `RagPolicyRetriever` implementing the existing `PolicyRetriever`
  protocol, alongside (not replacing) `LocalPolicyRetriever`.
- Policy documents (the versioned BRD section 9 rules) are embedded with a
  multilingual model (`sentence-transformers`,
  `paraphrase-multilingual-MiniLM-L12-v2`) into a local `chromadb` collection
  only at explicit seed time (`python -m app.seed_policy --verify`).
- Retrieval takes the claim category and effective date, returns the
  most relevant versioned `Policy` record; the selected policy version is
  still recorded on every evaluation and decision.
- **Hybrid rule**: retrieval only SELECTS the policy; evaluation stays the
  deterministic `LocalPolicyEvaluator`. A retrieval miss falls back to the
  local store and is audited — retrieval failure can never create an approval
  (FR-05 rule).
- Corpus documents are generated from the existing validated local policy records
  with BRD section 9 descriptions/source references. ID/version/effective date and
  complete rules remain identical; this PR does not introduce daily aggregation.
- Query uses a fixed category description; extracted keywords are deferred because
  the existing protocol does not accept them. No protocol or HTTP contract changes.
- Chroma uses cosine similarity and category/effective-date filters. Returned IDs,
  metadata and documents must match the trusted corpus/local record. Index text
  is never interpreted by a generative model.
- An immutable Hugging Face revision is pinned in code. Corpus/model fingerprint
  names each collection; stable document IDs make seed repeatable. Incomplete or
  missing generations fall back locally. Stop the API before reseeding, then restart.
- `POLICY_MODE=local|rag` defaults to local; `POLICY_INDEX_PATH` and
  `POLICY_MODEL_CACHE` default to ignored `./data/local/` directories. API requests
  only load cached model files and never seed/download. Shared adapter is cleared
  on application shutdown. Chroma telemetry is disabled.
- `policy.retrieved` audit/timeline provenance includes source, policy ID/version,
  fingerprint and classified reason. No raw exception messages or receipt data.

## Part 2 — ML anomaly scoring (FR-07)

- New `SklearnAnomalyScorer` implementing the existing `AnomalyScorer`
  protocol: an Isolation Forest trained on synthetic claim history (amounts,
  frequencies, category mix) at seed time, model version recorded on every
  Signal.
- Determinism: fixed random state, fixed feature schema; same input history
  produces the same score.
- Escalation-only: a high score can escalate (via the unchanged decision
  precedence) but never approves (FR-07 rule).
- The rule-based scorer remains available as fallback and for `missing
  history -> neutral` behaviour.

## Interfaces

- No new protocols; both upgrades replace implementations behind
  `PolicyRetriever` and `AnomalyScorer`.
- Selection: `POLICY_MODE=local|rag` and `ANOMALY_MODE=rules|ml` settings.

## Dependencies

RAG PR pins `chromadb==1.5.9` and `sentence-transformers==6.1.0`; resolve and
verify imports on existing Python 3.14 without changing the LangChain pins.
`scikit-learn` is a transitive embedding dependency; the anomaly adapter and its
explicit model/training configuration remain for the second PR.

## Acceptance criteria

- Decision outcomes are IDENTICAL between local and RAG retrieval for the
  seeded policy set (retrieval changes provenance, not outcomes).
- Anomaly scores are deterministic per (input, model version); evidence and
  model version appear on the Signal and in the timeline.
- All masking, audit-safety, and provider-failure rules from M7 apply.

## Tests

Retrieval parity (local vs rag on seeded corpus), fallback on retrieval
failure, anomaly determinism, threshold-boundary escalation parity with the
rule scorer, and mock-first tests that never require model downloads at test
time.
