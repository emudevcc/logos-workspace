"""Sanity checks for the typed settings loader."""

from app.core.config import get_settings


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.app_name == "English Cockpit OS"
    assert settings.ws_heartbeat_interval > 0
    assert settings.ws_heartbeat_timeout > 0
    assert settings.llm_base_url.endswith("/openai/v1")
    assert settings.cors_origins == []
    assert settings.deepgram_max_retries >= 0
    assert settings.deepgram_timeout_seconds > 0
    assert settings.host
    assert settings.llm_daily_limit >= 0
    assert settings.deepgram_daily_limit >= 0
