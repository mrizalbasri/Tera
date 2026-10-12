"""Reproducible independent synthetic employees; never reads application data."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random
from uuid import NAMESPACE_URL, uuid5

from app.integrations.ml_anomaly.features import CATEGORIES, CategoryContext, extract_features
from app.schemas.core import Claim

DATASET_VERSION = "synthetic-claims-v1"
SCENARIOS = ("normal", "amount_spike", "high_frequency", "repeated_amount", "category_shift")
BASE_AMOUNTS = (60_000, 100_000, 30_000, 350_000, 90_000)


@dataclass(frozen=True)
class SyntheticCase:
    claim: Claim
    history: tuple[Claim, ...]
    context: CategoryContext
    scenario: str

    def features(self) -> tuple[float, ...]:
        return extract_features(self.claim, self.claim.declared_amount, self.history, self.context)


def synthetic_cases(count: int, *, seed: int, anomalies: bool = False) -> list[SyntheticCase]:
    rng = Random(seed)
    cases = []
    for index in range(count):
        employee = f"synthetic-{seed}-{index}"
        now = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
        scenario = SCENARIOS[1 + index % 4] if anomalies else "normal"
        dominant = rng.randrange(len(CATEGORIES))
        secondary = (dominant + 1) % len(CATEGORIES)
        category = dominant if rng.random() < 0.8 else secondary
        if scenario == "category_shift":
            category = (dominant + 2) % len(CATEGORIES)
        scale = rng.uniform(0.7, 1.4)
        amount = int(BASE_AMOUNTS[category] * scale * rng.uniform(0.8, 1.2))
        if scenario == "amount_spike":
            amount *= rng.randint(8, 20)

        def record(number: int, value: int, date: datetime) -> Claim:
            return Claim(
                id=uuid5(NAMESPACE_URL, f"{employee}/{number}"), employee_id=employee,
                submitted_at=date, created_at=date, updated_at=date,
                currency="IDR", declared_amount=Decimal(value),
            )

        prior = []
        categories = {}
        elapsed = 0.0
        routine_repeats = rng.randint(0, 2) if not anomalies else 0
        for number in range(rng.randint(8, 24)):
            past_category = dominant if rng.random() < 0.8 else secondary
            elapsed += rng.uniform(2, 5) if scenario != "high_frequency" else rng.uniform(0.1, 0.3)
            value = int(BASE_AMOUNTS[past_category] * scale * rng.uniform(0.8, 1.2))
            if number < routine_repeats:
                value = amount
            if scenario == "repeated_amount" and number % 3 != 0:
                value = amount
            item = record(number, value, now - timedelta(days=elapsed))
            prior.append(item)
            categories[item.id] = CATEGORIES[past_category]
        # Exercise amount/frequency-only inference when category evidence is absent.
        context = CategoryContext(CATEGORIES[category], categories)
        if not anomalies and index % 5 == 0:
            context = CategoryContext()
        cases.append(SyntheticCase(record(-1, amount, now), tuple(prior), context, scenario))
    return cases
