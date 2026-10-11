"""Local embedding adapter; downloads are reserved for explicit seed commands."""

from typing import Protocol


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MODEL_IDENTITY = f"{MODEL_NAME}@{MODEL_REVISION}:normalized-cpu-v1"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceEmbedder:
    def __init__(self, cache_path: str, *, download: bool = False) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            MODEL_NAME, revision=MODEL_REVISION, cache_folder=cache_path,
            local_files_only=not download, device="cpu", trust_remote_code=False,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
