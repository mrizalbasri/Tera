"""Run explicitly: python -m app.seed_policy [--with-reranker] [--verify] [--benchmark]."""

import argparse
import json

from app.config import Settings
from app.integrations.rag.corpus import policy_documents
from app.integrations.rag.embeddings import SentenceEmbedder
from app.integrations.rag.index import seed_index
from app.integrations.rag.retriever import RagPolicyRetriever
from app.integrations.rag.reranker import CrossEncoderReranker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify actual model retrieval for every category")
    parser.add_argument("--with-reranker", action="store_true", help="Explicitly download/cache the pinned local reranker")
    parser.add_argument("--benchmark", action="store_true", help="Compare search/reranking on synthetic rule queries")
    args = parser.parse_args()
    settings = Settings()
    rerank_mode = "cross_encoder" if args.with_reranker or args.benchmark else settings.policy_rerank_mode
    if args.with_reranker or args.benchmark:
        # This CLI is the only place permitted to download model files.
        reranker = CrossEncoderReranker(settings.policy_reranker_cache, download=True)
        del reranker
    embedder = SentenceEmbedder(settings.policy_model_cache, download=True)
    fingerprint = seed_index(settings.policy_index_path, embedder)
    print(f"Policy index seeded: {fingerprint}")
    if args.verify:
        # Exercise the same offline model loader that API requests use.
        del embedder
        retriever = RagPolicyRetriever(
            settings.policy_index_path, settings.policy_model_cache,
            rerank_mode=rerank_mode, reranker_cache=settings.policy_reranker_cache,
            top_k=settings.policy_top_k, top_n=settings.policy_top_n,
        )
        for document in policy_documents():
            selection = retriever.retrieve_with_provenance(
                category=document.policy.category, effective_date=document.policy.effective_from,
            )
            if selection.source != "rag" or selection.policy != document.policy:
                raise RuntimeError(f"Policy parity failed: {document.policy.category}; {selection.reason}")
        print("Real-model retrieval parity verified for all 5 categories.")
        del retriever
    if args.benchmark:
        from app.integrations.rag.benchmark import benchmark
        from app.integrations.rag.embeddings import MODEL_IDENTITY
        from app.integrations.rag.index import PolicyIndex
        from app.integrations.rag.search import PolicySearch

        # A new adapter exercises the offline runtime path for each model.
        search = PolicySearch(PolicyIndex(settings.policy_index_path, policy_documents(), MODEL_IDENTITY),
                              settings.policy_model_cache)
        reranker = CrossEncoderReranker(settings.policy_reranker_cache)
        print(json.dumps(benchmark(search, reranker, top_k=settings.policy_top_k, top_n=settings.policy_top_n),
                         sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Policy setup failed ({type(exc).__name__}); check model cache/index configuration.") from None
