"""Fixed windows shared by all workers through the domain database."""

import time
from hashlib import sha256
from threading import Lock
from fastapi import Request

from app.errors import ApplicationError
from app.config import Settings


class MemoryRateLimiter:
    def __init__(self) -> None:
        self.windows: dict[str, tuple[int, int]] = {}
        self.lock = Lock()

    def consume_rate_limit(self, key: str, window: int, limit: int) -> bool:
        with self.lock:
            self.windows = {k: v for k, v in self.windows.items() if v[0] >= window - 2}
            previous, count = self.windows.get(key, (window, 0))
            count = count + 1 if previous >= window else 1
            self.windows[key] = (max(previous, window), count)
            return count <= limit


def enforce_write_limit(request: Request, user_id: str, settings: Settings) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    from app.api.deps import _backend

    backend = _backend(settings)
    store = backend if hasattr(backend, "consume_rate_limit") else backend.rate_limiter
    now = int(time.time())
    window = now // settings.rate_limit_window_seconds
    key = sha256(user_id.encode()).hexdigest()
    if not store.consume_rate_limit(key, window, settings.rate_limit_write_requests):
        raise ApplicationError("rate_limited", "Too many write requests; retry shortly.", 429,
                               {"retry_after": settings.rate_limit_window_seconds - now % settings.rate_limit_window_seconds})
