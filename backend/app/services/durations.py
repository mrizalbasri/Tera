from datetime import datetime


def elapsed_milliseconds(started_at: datetime | None, completed_at: datetime | None) -> int | None:
    if started_at is None or completed_at is None:
        return None
    return max(0, int((completed_at - started_at).total_seconds() * 1000))
