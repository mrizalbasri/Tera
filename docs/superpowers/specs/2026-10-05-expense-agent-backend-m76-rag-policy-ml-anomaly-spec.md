# Backend M7.6 — RAG Policy Retrieval and ML Anomaly Scoring Spec

## Purpose

Delivery starts with RAG policy selection (PR #17), followed by its modular
retrieval extension approved by the owner, then ML anomaly scoring in a separate
PR. M7.5 is merged; PostgreSQL remains the domain/checkpoint backend.

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
- The modular extension accepts optional internal typed context: canonical
  allowlisted concepts recognized in extracted items/vendor and bounded participant
  count. Arbitrary free text never becomes query text. Missing context uses the
  fixed category description. The PolicyRetriever protocol and HTTP contract stay
  unchanged; context is passed through the internal provenance method.
- Rule-level chunking keeps every condition/limit/exclusion together, retaining
  source and parent policy IDs. Chroma uses cosine similarity, top-k and
  category/effective-date filters. All candidates' IDs, metadata and text must
  match trusted chunks and complete local policies before optional reranking.
  Ranked chunks never reduce the rules evaluated from the full selected Policy.
- `POLICY_RERANK_MODE=none|cross_encoder` defaults to none. The pinned multilingual
  `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` runs locally on CPU with safetensors,
  validates finite scores, and returns top-n with stable tie breaking. Missing
  reranker or failed/invalid scoring falls back to the full local policy.
- Separate corpus, chunking, embedding, index, query, search, reranker and retrieval
  modules support independent tests. `POLICY_TOP_K=8`, `POLICY_TOP_N=3` are bounded
  to 1–50, with top-n <= top-k. The default corpus produces 15 atomic chunks.
- Immutable Hugging Face revisions are pinned in code. Corpus/chunk/model fingerprint
  names each collection; stable document IDs make seed repeatable. Incomplete or
  missing generations fall back locally. Stop the API before reseeding, then restart.
- `POLICY_MODE=local|rag` defaults to local; `POLICY_INDEX_PATH` and
  `POLICY_MODEL_CACHE` and `POLICY_RERANKER_CACHE` default to ignored `./data/local/` directories. API requests
  only load cached model files and never seed/download. Shared adapter is cleared
  on application shutdown. Chroma telemetry is disabled.
- `policy.retrieved` audit/timeline provenance includes source, policy ID/version,
  fingerprint, trusted chunk/rule IDs, candidate count, model identities and
  classified reason. No queries, raw exception messages or receipt data.

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

The modular extension adds atomic chunk/fingerprint tests, contextual privacy,
search filtering/candidate validation, reranking score validation/ties/top-n,
model-unavailable fallback, concurrency/restart and replay-safe audit. Both
search-only and reranked modes preserve policy/evaluation/decision parity.
`python -m app.seed_policy --with-reranker --verify --benchmark` performs a
separate real-model smoke and compares relevance/latency on synthetic rule queries.
Local tests include isolated PostgreSQL databases; GitHub CI remains manually
disabled at the owner's request. See [[2026-10-09-modular-policy-retrieval-design]].
