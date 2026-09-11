"""Process-level logging configuration with a size-capped rotating file.

The app configures no logging handler by default, so records propagate to the
root logger and reach whichever stream the deployment already captures — the
macOS LaunchAgent's ``data/logos-agent.log`` (stdout/stderr redirect) or
``journalctl`` on the Pi/systemd path. That has one operational gap: the
LaunchAgent's file grows without bound on the same volume as ``cockpit.db``.

:func:`configure_logging` closes it by attaching a ``RotatingFileHandler`` to
its own file, separate from the redirect target. Rotating a *separate* file is
deliberate: the process holds the LaunchAgent's file open for append, and
renaming that inode does not make the running process follow it — the renamed
archive would keep growing while the fresh file stayed empty. Because this
handler owns its file, rotation is correct with no restart and no root.

``configure_logging`` is called from :func:`app.__main__.main` — the real
process entrypoint — and never from ``create_app``, so tests never acquire a
file handler.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def resolve_level(name: str) -> int:
    """Map a level name to its logging constant, defaulting to ``INFO``.

    An unknown value (e.g. a typo in ``LOG_LEVEL``) must not stop the app from
    starting, so it degrades to ``INFO`` rather than raising.
    """
    level = logging.getLevelName(name.strip().upper())
    return level if isinstance(level, int) else logging.INFO


def configure_logging(settings: Settings) -> RotatingFileHandler | None:
    """Attach a rotating file handler to the root logger.

    Returns the handler, or ``None`` when file logging is disabled or the log
    directory cannot be created — a logging problem must never prevent startup.

    The handler is attached to the **root** logger so the ``app.*`` logger
    hierarchy (``app.services.llm``, ``app.services.bible_studies``, …)
    propagates into it without any per-module wiring.
    """
    if settings.log_max_bytes <= 0:
        return None

    root = logging.getLogger()
    root.setLevel(resolve_level(settings.log_level))

    # Idempotent: re-configuring (or a second uvicorn worker) must not stack
    # duplicate handlers, which would double every line.
    existing = _rotating_handler_for(root, settings.log_path)
    if existing is not None:
        return existing

    try:
        settings.log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            settings.log_path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
            delay=True,
        )
    except OSError:
        # Unwritable path (read-only checkout, bad mount): keep the stderr
        # behaviour the deployment already relies on.
        return None

    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)
    return handler


def _rotating_handler_for(root: logging.Logger, path: Path) -> RotatingFileHandler | None:
    """Return the already-installed handler writing to ``path``, if any."""
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(path):
            return handler
    return None
