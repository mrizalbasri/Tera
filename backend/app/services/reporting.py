"""Bounded batches avoid per-claim queries and full CSV buffering."""

import csv
import io
from collections import defaultdict
from collections.abc import Iterator, Sequence
from datetime import date
from uuid import UUID

from app.repositories.protocols import ClaimRepository, DecisionRepository, ProcessingRunRepository, SignalRepository
from app.repositories.query import ClaimFilter
from app.schemas.core import Claim, Decision
from app.services.durations import elapsed_milliseconds
from app.services.time_metrics import claim_time_metrics


class ReportingService:
    BATCH_SIZE = 200

    def __init__(
        self, claims: ClaimRepository, decisions: DecisionRepository | None = None,
        runs: ProcessingRunRepository | None = None, signals: SignalRepository | None = None,
    ) -> None:
        self.claims, self.decisions, self.runs, self.signals = claims, decisions, runs, signals

    def batches(self, filters: ClaimFilter) -> Iterator[Sequence[Claim]]:
        offset = 0
        while batch := self.claims.page(filters, limit=self.BATCH_SIZE, offset=offset):
            yield batch
            offset += len(batch)

    def summary(self, filters: ClaimFilter) -> dict[str, object]:
        if self.decisions is None or self.runs is None or self.signals is None:
            raise ValueError("Report summaries require decision, run, and signal repositories.")
        counts = dict(total_claims=0, approved_claims=0, rejected_claims=0, pending_claims=0,
                      automated_claims=0, manual_claims=0, duplicate_count=0, anomaly_count=0)
        duration_total = duration_count = 0
        active_total = employee_wait = reviewer_wait = measured = 0
        usage_runs = input_tokens = output_tokens = 0
        models: set[str] = set()
        for batch in self.batches(filters):
            ids = [claim.id for claim in batch]
            decisions: defaultdict[UUID, list[Decision]] = defaultdict(list)
            for decision in self.decisions.list_for_claims(ids):
                decisions[decision.claim_id].append(decision)
            batch_runs = list(self.runs.list_for_claims(ids))
            by_claim = defaultdict(list)
            for run in batch_runs:
                for usage in run.provider_usage:
                    if usage.get("status") == "measured":
                        usage_runs += 1
                        input_tokens += int(usage.get("input_tokens") or 0)
                        output_tokens += int(usage.get("output_tokens") or 0)
                    if isinstance(usage.get("model"), str):
                        models.add(usage["model"])
                by_claim[run.claim_id].append(run)
                duration = elapsed_milliseconds(run.started_at, run.completed_at)
                if duration is not None:
                    duration_total += duration
                    duration_count += 1
            for claim in batch:
                times = claim_time_metrics(by_claim[claim.id])
                if times["active_ms"] is not None:
                    measured += 1
                    active_total += times["active_ms"]
                employee_wait += times["employee_wait_ms"] or 0
                reviewer_wait += times["reviewer_wait_ms"] or 0
            for signal in self.signals.list_for_claims(ids):
                if signal.signal_type in ("duplicate", "anomaly"):
                    counts[f"{signal.signal_type}_count"] += 1
            for claim in batch:
                counts["total_claims"] += 1
                if claim.status in ("approved", "rejected"):
                    counts[f"{claim.status}_claims"] += 1
                    current = next((d for d in decisions[claim.id] if d.id == claim.current_decision_id), None)
                    if current is None and decisions[claim.id]:
                        current = decisions[claim.id][-1]
                    if current is not None:
                        counts["manual_claims" if current.created_by == "reviewer" else "automated_claims"] += 1
                else:
                    counts["pending_claims"] += 1
        return dict(period_from=filters.period_from, period_to=filters.period_to, **counts,
                    average_duration_ms=round(duration_total / duration_count) if duration_count else None,
                    estimated_time_saved_minutes=counts["automated_claims"] * 5,
                    time_saved_basis="assumption_5_minutes_per_automated_claim",
                    active_duration_ms=active_total if measured else None,
                    employee_wait_ms=employee_wait if measured else None,
                    reviewer_wait_ms=reviewer_wait if measured else None,
                    measured_claims=measured,
                    provider_cost=None, provider_cost_basis="unavailable",
                    provider_input_tokens=input_tokens if usage_runs else None,
                    provider_output_tokens=output_tokens if usage_runs else None,
                    provider_measured_calls=usage_runs, provider_models=sorted(models))

    def csv_rows(self, filters: ClaimFilter) -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["claim_id", "employee_id", "submitted_at", "currency", "declared_amount", "status"])
        yield buffer.getvalue()
        for batch in self.batches(filters):
            buffer.seek(0)
            buffer.truncate()
            for claim in batch:
                writer.writerow([claim.id, self._csv_cell(claim.employee_id), claim.submitted_at.isoformat(),
                                 self._csv_cell(claim.currency), str(claim.declared_amount) if claim.declared_amount is not None else "", claim.status])
            yield buffer.getvalue()

    @staticmethod
    def _csv_cell(value: str) -> str:
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value
