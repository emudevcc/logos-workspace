"""Application configuration loaded from environment variables.

All settings are typed and validated with pydantic-settings. Environment
variable names follow the repository README (for example ``COCKPIT_DB`` and
``LLM_API_KEY``), so the deploy target needs no code changes to override them.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_LLM_MODEL = "qwen/qwen3.8-27b"


class Settings(BaseSettings):
    """Runtime configuration for the Cockpit backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Logos Workspace"
    host: str = "127.0.0.1"
    port: int = 8000

    tls_certfile: str = Field(default="", validation_alias="TLS_CERTFILE")
    tls_keyfile: str = Field(default="", validation_alias="TLS_KEYFILE")

    db_path: Path = Field(
        default=Path("data/cockpit.db"),
        validation_alias="COCKPIT_DB",
        description="Filesystem location of the SQLite database.",
    )
    static_dir: Path = Field(default=Path("static"))
    templates_dir: Path = Field(default=Path("templates"))

    ws_heartbeat_interval: float = Field(default=25.0, gt=0.0)
    ws_heartbeat_timeout: float = Field(default=60.0, gt=0.0)
    ws_max_connections: int = Field(default=100, ge=1)

    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    content_cache_ttl_seconds: float = Field(default=300.0, gt=0.0)
    dictionary_cache_ttl_seconds: float = Field(default=86400.0, gt=0.0)
    rate_limit_per_minute: int = Field(default=30, ge=1)
    new_cards_per_day: int = Field(default=10, ge=1)
    daily_review_goal: int = Field(default=20, ge=1)

    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default=DEFAULT_LLM_BASE_URL,
        validation_alias="LLM_BASE_URL",
    )
    llm_model: str = Field(default=DEFAULT_LLM_MODEL, validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=60.0, gt=0.0)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_daily_limit: int = Field(default=1000, ge=0)

    deepgram_api_key: str = Field(default="", validation_alias="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-2")
    deepgram_max_retries: int = Field(default=2, ge=0)
    deepgram_timeout_seconds: float = Field(default=300.0, gt=0.0)
    deepgram_allowed_hosts: list[str] = Field(
        default_factory=list, validation_alias="DEEPGRAM_ALLOWED_HOSTS"
    )
    deepgram_daily_limit: int = Field(default=200, ge=0)

    stt_provider: Literal["deepgram", "whisper"] = Field(
        default="deepgram", validation_alias="STT_PROVIDER"
    )
    whisper_base_url: str = Field(
        default="http://localhost:8080", validation_alias="WHISPER_BASE_URL"
    )
    whisper_max_retries: int = Field(default=2, ge=0, validation_alias="WHISPER_MAX_RETRIES")
    whisper_timeout_seconds: float = Field(
        default=300.0, gt=0.0, validation_alias="WHISPER_TIMEOUT_SECONDS"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (environment is read once per process)."""
    return Settings()
