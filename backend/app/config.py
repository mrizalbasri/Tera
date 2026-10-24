import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().casefold()
    return (
        not normalized
        or normalized in {"change_me", "changeme", "your-api-key"}
        or normalized.startswith(("replace_with", "your-", "your_", "<"))
    )


class Settings(BaseSettings):
    app_name: str = "Expense Agent API"
    environment: Literal["development", "test", "production"] = "development"
    demo_mode: bool = False
    frontend_origin: str = "http://localhost:5173"
    clerk_issuer: str = ""
    clerk_admin_user_ids: str = ""
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
    max_receipt_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    max_receipts_per_claim: int = Field(default=10, ge=1, le=50)
    max_upload_total_bytes: int = Field(default=25 * 1024 * 1024, ge=1, le=500 * 1024 * 1024)
    max_request_bytes: int = Field(default=26 * 1024 * 1024, ge=1, le=501 * 1024 * 1024)
    claim_lock_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    recovery_interval_seconds: int = Field(default=30, ge=1, le=3600)
    max_recovery_attempts: int = Field(default=3, ge=1, le=10)
    rate_limit_write_requests: int = Field(default=60, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    auto_approve_amount_limit: int = Field(default=500_000, gt=0)
    auto_approve_min_confidence: float = Field(default=0.8, ge=0, le=1)
    escalation_amount_threshold: int = Field(default=500_000, gt=0)
    max_processing_retries: int = Field(default=2, ge=0, le=5)
    max_clarification_rounds: int = Field(default=3, ge=1, le=10)
    extraction_confidence_threshold: float = Field(default=0.8, gt=0, le=1)
    max_claim_age_days: int = Field(default=14, ge=1)
    anomaly_escalation_threshold: float = Field(default=0.7, gt=0, le=1)
    llm_base_url: str = "https://api.z.ai/api/paas/v4"
    llm_model: str = "glm-4.5v"
    llm_api_key: str = ""
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    provider_fallback: Literal["none", "mock"] = "none"
    # Pixel-level redaction is not attempted (unreliable without a local OCR
    # pass); "block" fails closed and routes images to the local mock instead.
    llm_image_privacy_mode: Literal["send", "block"] = "send"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", hide_input_in_errors=True)

    @model_validator(mode="after")
    def validate_policy_retrieval(self) -> "Settings":
        if self.demo_mode:
            if self.environment == "production":
                raise ValueError("demo_mode is not allowed in production")
            self.storage_backend = "memory"
            self.provider_mode = "mock"
            self.policy_mode = "local"
            self.anomaly_mode = "rules"
        if self.policy_index_schema in ("public", "pg_catalog", "information_schema", self.graph_checkpoint_schema):
            raise ValueError("policy_index_schema must be separate from domain and checkpoint schemas")
        if self.policy_top_n > self.policy_top_k:
            raise ValueError("policy_top_n must not exceed policy_top_k")
        if self.environment == "production":
            from sqlalchemy.engine import make_url

            if self.storage_backend != "sql" or make_url(self.database_url).get_backend_name() != "postgresql":
                raise ValueError("production requires PostgreSQL storage")
            url = make_url(self.database_url)
            if _is_placeholder(url.password or "") or (url.password or "").strip().casefold() in ("postgres", "password"):
                raise ValueError("production requires non-placeholder database credentials")
            if self.provider_mode != "live" or _is_placeholder(self.llm_api_key) or self.provider_fallback != "none":
                raise ValueError("production requires live provider credentials and no mock fallback")
            if _is_placeholder(self.llm_model):
                raise ValueError("production requires a configured provider model")
            for name in ("frontend_origin", "clerk_issuer", "llm_base_url"):
                value = urlparse(getattr(self, name))
                if value.scheme != "https" or not value.hostname or value.username or value.password:
                    raise ValueError(f"production requires a valid HTTPS {name}")
                hostname = value.hostname.casefold()
                if _is_placeholder(hostname) or any(
                    hostname == domain or hostname.endswith(f".{domain}")
                    for domain in ("example.com", "example.org", "example.net")
                ):
                    raise ValueError(f"production requires a non-placeholder {name}")
                if name in ("frontend_origin", "clerk_issuer") and (value.path not in ("", "/") or value.query or value.fragment):
                    raise ValueError(f"{name} must be an origin without a path, query, or fragment")
            admin_ids = [value.strip() for value in self.clerk_admin_user_ids.split(",") if value.strip()]
            if not admin_ids or any(re.fullmatch(r"user_[A-Za-z0-9]+", value) is None for value in admin_ids):
                raise ValueError("production requires configured Clerk issuer and admin IDs")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
