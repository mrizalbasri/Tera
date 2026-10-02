from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict[str, Any] | None = None
