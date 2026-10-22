"""Small in-process sliding-window rate limiter (one Render instance is enough for login throttling)."""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import AppError
from app.core.i18n import tr


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = max(1, int(self.window - (now - q[0])))
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    tr(f"محاولات دخول كثيرة، حاول مرة أخرى بعد {retry} ثانية", f"Too many login attempts, try again in {retry} seconds"),
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    # Render (and most PaaS) put the real client IP first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
