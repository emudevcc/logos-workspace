"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request, status


def rate_limited(request: Request) -> None:
    limiter = request.app.state.rate_limiter
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
