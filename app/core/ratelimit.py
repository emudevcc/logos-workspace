"""In-memory sliding-window rate limiter (single process, no persistence)."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Allow at most ``max_requests`` per ``window_seconds`` per key."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self._window:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(now)
        return True
