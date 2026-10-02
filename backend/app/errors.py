from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(ApplicationError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            code="not_found",
            message=f"{resource} '{identifier}' was not found.",
            status_code=404,
        )


class InvalidStateTransitionError(ApplicationError):
    def __init__(self, resource: str, current: str, target: str) -> None:
        super().__init__(
            code="invalid_state_transition",
            message=f"{resource} cannot transition from '{current}' to '{target}'.",
            status_code=409,
        )
