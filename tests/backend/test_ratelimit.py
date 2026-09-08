"""Tests for the rate limiter and its endpoint wiring."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.ratelimit import RateLimiter
from app.main import create_app
from tests.backend.helpers import FakeLLM


def test_rate_limiter_limits_within_window() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60.0)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True


def test_rate_limit_endpoint_returns_429(tmp_path: Path) -> None:
    os.environ["COCKPIT_DB"] = str(tmp_path / "db.sqlite")
    os.environ["RATE_LIMIT_PER_MINUTE"] = "1"
    get_settings.cache_clear()

    llm = FakeLLM(
        result={"revised": "tight", "cut_phrases": [], "verb_upgrades": [], "tone": "direct"}
    )
    app = create_app(llm=llm)
    try:
        with TestClient(app) as client:
            first = client.post("/api/declutter", json={"draft": "In order to test this."})
            second = client.post("/api/declutter", json={"draft": "In order to test this."})
            assert first.status_code == 200
            assert second.status_code == 429
    finally:
        get_settings.cache_clear()
        os.environ.pop("COCKPIT_DB", None)
        os.environ.pop("RATE_LIMIT_PER_MINUTE", None)
