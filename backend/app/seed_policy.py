"""Run explicitly: python -m app.seed_policy [--verify]."""

import argparse

from app.config import Settings
from app.integrations.rag.corpus import policy_documents
from app.integrations.rag.policy import RagPolicyRetriever, SentenceEmbedder, seed_index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify actual model retrieval for every category")
    args = parser.parse_args()
    settings = Settings()
    embedder = SentenceEmbedder(settings.policy_model_cache, download=True)
    fingerprint = seed_index(settings.policy_index_path, embedder)
    print(f"Policy index seeded: {fingerprint}")
    if args.verify:
        # Exercise the same offline model loader that API requests use.
        del embedder
        retriever = RagPolicyRetriever(settings.policy_index_path, settings.policy_model_cache)
        for document in policy_documents():
            selection = retriever.retrieve_with_provenance(
                category=document.policy.category, effective_date=document.policy.effective_from,
            )
            if selection.source != "rag" or selection.policy != document.policy:
                raise RuntimeError(f"Policy parity failed: {document.policy.category}; {selection.reason}")
        print("Real-model retrieval parity verified for all 5 categories.")


if __name__ == "__main__":
    main()
