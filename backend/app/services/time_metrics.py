from datetime import UTC, datetime


def interval_milliseconds(intervals: list[tuple[datetime, datetime]]) -> int:
    merged: list[list[datetime]] = []
    for start, end in sorted(intervals):
        if end < start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return round(sum((end - start).total_seconds() * 1000 for start, end in merged))


def claim_time_metrics(runs, *, now: datetime | None = None) -> dict[str, int | None]:
    now = now or datetime.now(UTC)
    ordered = sorted((r for r in runs if r.started_at is not None), key=lambda r: r.started_at)
    active, employee, reviewer = [], [], []
    for index, run in enumerate(ordered):
        if run.completed_at is not None:
            active.append((run.started_at, run.completed_at))
            next_start = ordered[index + 1].started_at if index + 1 < len(ordered) else now
            if run.status == "needs_clarification":
                employee.append((run.completed_at, min(next_start, now)))
            elif run.status == "escalated":
                reviewer.append((run.completed_at, min(next_start, now)))
    return {"active_ms": interval_milliseconds(active) if active else None,
            "employee_wait_ms": interval_milliseconds(employee) if ordered else None,
            "reviewer_wait_ms": interval_milliseconds(reviewer) if ordered else None}
