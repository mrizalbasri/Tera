# Backend M7.6 — RAG Policy Retrieval and ML Anomaly Scoring Spec

## Purpose

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
  at startup or seed time.
- Retrieval takes the claim category (and extracted keywords), returns the
  most relevant versioned `Policy` record; the selected policy version is
  still recorded on every evaluation and decision.
- **Hybrid rule**: retrieval only SELECTS the policy; evaluation stays the
  deterministic `LocalPolicyEvaluator`. A retrieval miss falls back to the
  local store and is audited — retrieval failure can never create an approval
  (FR-05 rule).

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

`chromadb`, `sentence-transformers`, `scikit-learn` (pinned).

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
