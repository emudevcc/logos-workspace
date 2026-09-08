"""Shared UTC time helpers.

All persisted timestamps use one canonical format (ISO-8601 with a ``+00:00``
offset and second precision) so lexicographic SQLite comparisons are correct.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC ``datetime``."""
    return datetime.now(UTC)


def iso_utc(dt: datetime) -> str:
    """Serialize to the canonical UTC string: ``YYYY-MM-DDTHH:MM:SSZ``.

    The trailing ``Z`` and second precision match the SQLite ``strftime``
    defaults in ``app/core/db.py`` so lexicographic comparisons are correct.
    """
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
