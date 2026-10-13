"""Control-only checkpoint state and invocation-local review context."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from app.schemas.core import Claim, Decision, Review


class ClaimGraphState(TypedDict):
    claim_id: str
    run_id: str
    pipeline_version: str
    stage: str


@dataclass
class ReviewExecution:
    """Request-local callback and result; never serialized into checkpoints."""

    apply: Callable[[UUID], tuple[Claim, Decision, Review]]
    result: tuple[Claim, Decision, Review] | None = None
