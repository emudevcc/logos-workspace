"""Daily spend budget: caps paid external calls over a rolling 24-hour window."""

from __future__ import annotations

from app.core.ratelimit import RateLimiter


class SpendBudget:
    """Allow at most ``daily_limit`` calls per rolling 24 hours.

    A limit of zero means unlimited.
    """

    def __init__(self, daily_limit: int) -> None:
        self._unlimited = daily_limit <= 0
        self._limiter = RateLimiter(max_requests=max(daily_limit, 1), window_seconds=86400.0)

    def consume(self) -> bool:
        if self._unlimited:
            return True
        return self._limiter.allow("global")
