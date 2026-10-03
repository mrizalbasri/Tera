from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Expense Agent API"
    environment: Literal["development", "test", "production"] = "development"
    frontend_origin: str = "http://localhost:5173"
    storage_backend: Literal["memory", "sql"] = "memory"
    database_url: str = "sqlite:///./expense_agent.db"
    provider_mode: Literal["mock", "live"] = "mock"
    max_receipt_size_bytes: int = 10 * 1024 * 1024
    auto_approve_amount_limit: int = 500_000
    auto_approve_min_confidence: float = 0.8
    escalation_amount_threshold: int = 500_000
    max_processing_retries: int = 2
    extraction_confidence_threshold: float = 0.8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
