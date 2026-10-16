from dataclasses import dataclass
from datetime import date

from app.errors import ApplicationError
from app.schemas.core import Claim


@dataclass(frozen=True)
class ClaimFilter:
    employee_id: str | None = None
    status: str | None = None
    period_from: date | None = None
    period_to: date | None = None

    def __post_init__(self) -> None:
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise ApplicationError("invalid_period", "period_from must not exceed period_to.", 422)

    def matches(self, claim: Claim) -> bool:
        day = claim.submitted_at.date()
        return (
            (self.employee_id is None or claim.employee_id == self.employee_id)
            and (self.status is None or claim.status == self.status)
            and (self.period_from is None or day >= self.period_from)
            and (self.period_to is None or day <= self.period_to)
        )
