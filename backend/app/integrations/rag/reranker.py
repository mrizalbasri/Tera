"""Optional local cross-encoder: score query/chunk pairs, never generate rules."""

from math import isfinite
from typing import Protocol

from app.integrations.rag.errors import RetrievalError
from app.integrations.rag.search import Candidate


RERANK_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANK_MODEL_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"
RERANK_MODEL_IDENTITY = f"{RERANK_MODEL_NAME}@{RERANK_MODEL_REVISION}:cpu-max512-v1"


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, cache_path: str, *, download: bool = False) -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(
            RERANK_MODEL_NAME, revision=RERANK_MODEL_REVISION, cache_folder=cache_path,
            device="cpu", max_length=512, trust_remote_code=False,
            local_files_only=not download, model_kwargs={"use_safetensors": True},
        )

    def score(self, query: str, texts: list[str]) -> list[float]:
        return self.model.predict(
            [(query, text) for text in texts], batch_size=8, show_progress_bar=False,
        ).reshape(-1).tolist()


def rerank_candidates(query: str, candidates: list[Candidate], reranker: Reranker, top_n: int) -> list[Candidate]:
    scores = reranker.score(query, [candidate.text for candidate in candidates])
    try:
        if len(scores) != len(candidates) or any(isinstance(score, bool) or not isfinite(float(score)) for score in scores):
            raise ValueError
        ranked = sorted(zip(candidates, scores, strict=True),
                        key=lambda pair: (-float(pair[1]), pair[0].chunk_id))
    except (TypeError, ValueError, OverflowError):
        raise RetrievalError("rerank_invalid") from None
    return [candidate for candidate, _ in ranked[:top_n]]
