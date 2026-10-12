from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Expense Agent API"
    environment: Literal["development", "test", "production"] = "development"
    frontend_origin: str = "http://localhost:5173"
    storage_backend: Literal["memory", "sql"] = "memory"
    database_url: str = "postgresql+psycopg://postgres:change_me@127.0.0.1:5432/tera"
    graph_checkpoint_path: str = "./expense_agent_checkpoints.db"
    graph_checkpoint_schema: str = "langgraph"
    provider_mode: Literal["mock", "live"] = "mock"
    policy_mode: Literal["local", "rag"] = "local"
    anomaly_mode: Literal["rules", "ml"] = "rules"
    anomaly_model_path: str = "./data/local/anomaly/model.joblib"
    policy_index_schema: str = Field(default="rag", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    # Accepted for existing dotenv files only; pgvector ignores old Chroma paths.
    policy_index_path: str | None = Field(default=None, exclude=True)
    policy_model_cache: str = "./data/local/policy_model"
    policy_reranker_cache: str = "./data/local/policy_reranker"
    policy_rerank_mode: Literal["none", "cross_encoder"] = "none"
    policy_top_k: int = Field(default=8, ge=1, le=50)
    policy_top_n: int = Field(default=3, ge=1, le=50)
    max_receipt_size_bytes: int = 10 * 1024 * 1024
    auto_approve_amount_limit: int = 500_000
    auto_approve_min_confidence: float = 0.8
    escalation_amount_threshold: int = 500_000
    max_processing_retries: int = 2
    extraction_confidence_threshold: float = 0.8
    max_claim_age_days: int = 14
    anomaly_escalation_threshold: float = Field(default=0.7, gt=0, le=1)
    llm_base_url: str = "https://api.z.ai/api/paas/v4"
    llm_model: str = "glm-4.5v"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    provider_fallback: Literal["none", "mock"] = "none"
    # Pixel-level redaction is not attempted (unreliable without a local OCR
    # pass); "block" fails closed and routes images to the local mock instead.
    llm_image_privacy_mode: Literal["send", "block"] = "send"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_policy_retrieval(self) -> "Settings":
        if self.policy_index_schema in ("public", "pg_catalog", "information_schema", self.graph_checkpoint_schema):
            raise ValueError("policy_index_schema must be separate from domain and checkpoint schemas")
        if self.policy_top_n > self.policy_top_k:
            raise ValueError("policy_top_n must not exceed policy_top_k")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
