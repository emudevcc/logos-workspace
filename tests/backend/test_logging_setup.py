"""Tests for the size-capped rotating log handler."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.logging_setup import configure_logging, resolve_level


@pytest.fixture(autouse=True)
def _restore_root_logger() -> object:
    """Keep the process-wide root logger unchanged across tests."""
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level)


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "log_path": tmp_path / "logs" / "app.log",
        "log_max_bytes": 1000,
        "log_backup_count": 2,
        "log_level": "INFO",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_resolve_level_accepts_names_and_defaults_unknown_to_info() -> None:
    assert resolve_level("debug") == logging.DEBUG
    assert resolve_level("  WARNING ") == logging.WARNING
    assert resolve_level("ERROR") == logging.ERROR
    # A typo must not crash startup.
    assert resolve_level("not-a-level") == logging.INFO


def test_configure_logging_creates_handler_and_parent_dir(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    assert not settings.log_path.parent.exists()

    handler = configure_logging(settings)

    assert isinstance(handler, RotatingFileHandler)
    assert settings.log_path.parent.is_dir()
    assert handler in logging.getLogger().handlers


def test_records_reach_the_file_and_honor_level(tmp_path: Path) -> None:
    settings = _settings(tmp_path, log_level="WARNING")
    configure_logging(settings)
    logger = logging.getLogger("app.services.llm")

    logger.info("should be filtered out")
    logger.warning("should be written")
    logging.shutdown()
    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = settings.log_path.read_text(encoding="utf-8")
    assert "should be written" in contents
    assert "should be filtered out" not in contents
    # The format the deployment greps for: level and logger name are present.
    assert "WARNING app.services.llm" in contents


def test_rotation_caps_file_size(tmp_path: Path) -> None:
    """The whole point: the live file must not grow past maxBytes."""
    settings = _settings(tmp_path, log_max_bytes=1000, log_backup_count=2)
    handler = configure_logging(settings)
    assert handler is not None
    logger = logging.getLogger("app.test.rotation")

    for index in range(200):
        logger.warning("rotation filler line number %04d padding padding", index)
        handler.flush()

    rotated = sorted(settings.log_path.parent.glob("app.log*"))
    assert len(rotated) > 1, "expected the log to have been rotated at least once"
    # The live file is capped; a backup took the overflow.
    assert settings.log_path.stat().st_size <= 1000
    assert (settings.log_path.parent / "app.log.1").exists()


def test_backup_count_is_honored(tmp_path: Path) -> None:
    settings = _settings(tmp_path, log_max_bytes=500, log_backup_count=2)
    handler = configure_logging(settings)
    assert handler is not None
    logger = logging.getLogger("app.test.backups")

    for index in range(400):
        logger.warning("backup filler line number %04d padding padding", index)
        handler.flush()

    # backupCount=2 means at most .1 and .2 alongside the live file.
    assert (settings.log_path.parent / "app.log.2").exists()
    assert not (settings.log_path.parent / "app.log.3").exists()


def test_disabled_when_max_bytes_is_zero(tmp_path: Path) -> None:
    settings = _settings(tmp_path, log_max_bytes=0)
    assert configure_logging(settings) is None
    assert not settings.log_path.exists()
    assert not any(
        isinstance(h, RotatingFileHandler) for h in logging.getLogger().handlers
    )


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = configure_logging(settings)
    second = configure_logging(settings)

    assert first is second
    matching = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, RotatingFileHandler) and h.baseFilename == str(settings.log_path)
    ]
    assert len(matching) == 1


def test_unwritable_path_degrades_instead_of_raising(tmp_path: Path) -> None:
    # A path whose parent is an existing *file* cannot become a directory.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    settings = _settings(tmp_path, log_path=blocker / "nested" / "app.log")

    assert configure_logging(settings) is None
