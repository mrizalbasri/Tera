"""Shared, versioned feature extraction for training and inference."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from math import isfinite, log1p
from uuid import UUID

from app.schemas.core import Claim

FEATURE_VERSION = "claim-features-v1"
FEATURE_NAMES = (
    "log_total", "log_amount_ratio", "claims_last_7_days",
    "repeated_amount_share", "category_history_share",
)
MIN_HISTORY = 3
CATEGORIES = ("meals", "fuel", "toll_parking", "hotel", "other")


@dataclass(frozen=True)
class CategoryContext:
    category: str | None = None
    history_categories: Mapping[UUID, str] = field(default_factory=dict)


def prior_history(claim: Claim, history: Sequence[Claim]) -> list[Claim]:
    """Exclude self, future, other employee/currency and unusable amounts."""
    return sorted((
        prior for prior in history
        if prior.id != claim.id and prior.employee_id == claim.employee_id
        and prior.currency == claim.currency and prior.submitted_at < claim.submitted_at
        and prior.declared_amount is not None and prior.declared_amount.is_finite()
        and 0 < prior.declared_amount <= Decimal("1e15")
    ), key=lambda prior: (prior.submitted_at, str(prior.id)))


def extract_features(
    claim: Claim, total: Decimal, history: Sequence[Claim],
    context: CategoryContext | None = None,
) -> tuple[float, ...]:
    if not total.is_finite() or not 0 < total <= Decimal("1e15"):
        raise ValueError("invalid anomaly total")
    prior = prior_history(claim, history)
    if len(prior) < MIN_HISTORY:
        raise ValueError("insufficient history")
    context = context or CategoryContext()
    known = [p for p in prior if context.history_categories.get(p.id) in CATEGORIES]
    matching = [p for p in known if context.history_categories[p.id] == context.category]
    baseline = matching if matching else prior
    average = sum((p.declared_amount for p in baseline), Decimal("0")) / len(baseline)
    values = (
        log1p(float(total)), log1p(float(total / average)),
        float(sum(claim.submitted_at - p.submitted_at <= timedelta(days=7) for p in prior)),
        sum(p.declared_amount == total for p in prior) / len(prior),
        len(matching) / len(known) if known and context.category in CATEGORIES else 0.5,
    )
    if not all(isfinite(value) for value in values):
        raise ValueError("nonfinite anomaly features")
    return values
