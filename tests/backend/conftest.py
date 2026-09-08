"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import Database
from app.main import create_app
from app.services.deepgram import DeepgramProvider
from app.services.llm import LLMProvider
from tests.backend.helpers import ClientFactory, make_mock_http


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[Database]:
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def client_factory(tmp_path: Path) -> Iterator[ClientFactory]:
    """Build a ``TestClient`` with an isolated DB and optional mock HTTP/LLM."""
    os.environ["COCKPIT_DB"] = str(tmp_path / "cockpit.db")
    os.environ["STT_PROVIDER"] = "deepgram"  # isolate tests from the local .env
    get_settings.cache_clear()

    def _build(
        handler: Callable[[httpx.Request], httpx.Response] | None = None,
        llm: LLMProvider | None = None,
        deepgram: DeepgramProvider | None = None,
    ) -> TestClient:
        http = make_mock_http(handler) if handler is not None else None
        return TestClient(create_app(http_client=http, llm=llm, deepgram=deepgram))

    yield _build

    get_settings.cache_clear()
    os.environ.pop("COCKPIT_DB", None)
    os.environ.pop("STT_PROVIDER", None)
