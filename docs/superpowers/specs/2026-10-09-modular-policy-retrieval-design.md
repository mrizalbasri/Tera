# Modular policy retrieval

## Scope and delivery

Implement the owner's approved RAG extension: rule-level chunking, local
embeddings, filtered top-k search, configurable local cross-encoder reranking,
and bounded contextual queries. Branch `feat/rag-retrieval` starts from
`feat/rag-policy` while PR #17 is open. This change depends on that PR and does
not merge it. ML anomaly, OCR, frontend, reporting and issue #12 remain outside
scope. Tests run locally; the manually disabled GitHub workflow stays disabled.

## Modules and data flow

- `corpus.py`: trusted versioned Policy documents derived from BRD section 9.
- `chunking.py`: one atomic rule per chunk, including every rule field and
  policy/source identity. The no-rule category receives an explicit summary.
  Limits, required terms and exclusions are never split apart. Stable chunk IDs
  and chunk content participate in the corpus/model fingerprint.
- `embeddings.py`: the existing pinned multilingual SentenceTransformer, CPU,
  cached-only in API requests.
- `index.py`: explicit Chroma seed/upsert, immutable fingerprint generations,
  lazy read-only opening and readiness checks. No request-time seeding.
- `query.py`: immutable context built from recognized policy concepts in vendor
  and line-item descriptions, plus bounded participant count. Only allowlisted
  canonical labels enter the query; arbitrary receipt text, identities, amounts,
  answers and credentials are excluded. Query text stays ephemeral.
- `search.py`: category/date metadata filtering, top-k cosine search, strict
  validation of every returned ID, metadata and text against the trusted chunks.
- `reranker.py`: pinned `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, local CPU;
  finite one-score-per-candidate validation, deterministic tie breaking, top-n.
- `retriever.py`: shared adapter/lock, orchestration and safe provenance. The
  final result is always the complete canonical Policy, never only ranked rules.

Ingestion: documents -> atomic chunks -> embeddings -> persistent Chroma.
Request: category/date + safe concepts -> embedding -> filtered top-k ->
optional reranking -> validated full Policy -> unchanged deterministic evaluator.

## Compatibility, failures and privacy

The public HTTP contract and PolicyRetriever.retrieve signature stay unchanged.
The internal provenance method accepts optional typed context. The extraction
service constructs that context; local mode keeps existing behavior.

POLICY_MODE remains local by default. POLICY_RERANK_MODE is none by default
until relevance/latency evaluation justifies enabling cross_encoder. Top-k
defaults to 8 and top-n to 3, with positive bounded settings and top-n <= top-k.
Separate ignored caches hold the embedding and reranker models. No new package
is needed: the pinned sentence-transformers dependency supplies CrossEncoder.

Missing/incomplete index, unavailable models, malformed candidates or scores,
and retrieval/reranking exceptions fall back to LocalPolicyRetriever with a
classified reason. Local unavailability retains the existing 503 behavior.
Audit records contain trusted policy/chunk/rule IDs, fingerprints, pinned model
identities and reason codes only, never queries, receipt text or raw exceptions.
Queries do not enter checkpoints or Chroma. Index text remains policy-only.

Explicit seed can download public pinned models; API loaders use
local_files_only=True and trust_remote_code=False. Corpus/chunk changes create a
new generation, so existing installations must reseed with the API stopped and
restart afterward. Old generations are retained. User provider settings and
PostgreSQL storage are preserved.

## Validation and completion

Retain all baseline policy/evaluation/decision parity tests, updating seed counts
and module seams for rule chunks. Add coverage for complete rule chunks, stable
IDs/fingerprints, contextual query privacy/bounds, top-k/filtering, top-n and ties,
invalid candidates/scores, missing reranker, replay-safe audit, concurrency and
persistent reopening. Routine tests use fake embeddings/reranker and temporary
real Chroma without downloads or external APIs.

An explicit real-model verification command seeds the index, verifies all five
full policies, and reports search/reranked relevance plus warmed latency on a
fixed synthetic rule-query benchmark. Report regressions honestly; reranking is
not claimed to improve compliance outcomes because full-policy evaluation is
unchanged. Verify actual cached-only runtime paths for both models. Run the full
backend suite including isolated PostgreSQL cases. No merge without user approval.

## References

- https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html
- https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
- https://sbert.net/docs/package_reference/cross_encoder/model.html

## Local validation — 2026-10-09

- Full backend suite: **339 passed** in 83.93 seconds, including isolated
  PostgreSQL cases, all previous 254 cases, and 85 additional cases. One Chroma
  deprecation warning concerns Python 3.16; no dependency pins changed and
  `pip check` reports no broken requirements.
- Real-model offline seed/verification succeeded for all five policies, producing
  15 chunks. Index fingerprint:
  `7e87ce2895a0d67f4aa58e0652941390c5cc2d4196459f1bdb7a0d069829d46c`.
- Both real cached models also ran through the HTTP claim-processing path for
  all five categories with synthetic mock extraction and memory claim storage.
  Every retrieval audit recorded RAG and the pinned reranker; no LLM endpoint
  was called and no application claims were written to PostgreSQL.
- On nine fixed synthetic concept/rule pairs, top-1 evidence relevance changed
  from 4/9 (44.4%) to 7/9 (77.8%); MRR at 3 changed from 0.648 to 0.889.
  Mean warmed search was 25.76 ms and additional reranking 153.21 ms on this
  laptop during the smoke run. This small benchmark is not representative of
  arbitrary company documents and does not measure claim decision accuracy.
- Default modes remain local/none; enabling rag/cross_encoder is explicit.
  Existing local provider settings were preserved. GitHub workflow state was
  verified as `disabled_manually`; all verification above ran locally.
