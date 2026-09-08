"""Discourse-connector detection for transcript highlighting.

Pure and offline: given a transcript string, return the character offsets of
discourse connectors (e.g. "furthermore", "on the other hand") so the frontend
teleprompter can highlight them in real time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DISCOURSE_CONNECTORS: tuple[str, ...] = (
    "furthermore",
    "moreover",
    "however",
    "nevertheless",
    "nonetheless",
    "on the other hand",
    "on the contrary",
    "therefore",
    "consequently",
    "as a result",
    "in addition",
    "additionally",
    "for example",
    "for instance",
    "in contrast",
    "by contrast",
    "meanwhile",
    "in conclusion",
    "in summary",
    "in particular",
    "similarly",
    "likewise",
)

# Longest-first so a phrase like "on the other hand" is matched whole rather
# than being shadowed by a shorter alternative.
_CONNECTOR_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])({alternatives})(?![A-Za-z0-9])".format(
        alternatives="|".join(
            re.escape(c) for c in sorted(DISCOURSE_CONNECTORS, key=len, reverse=True)
        )
    ),
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ConnectorMatch:
    connector: str
    index: int


def find_connectors(text: str) -> list[ConnectorMatch]:
    """Return case-insensitive connector matches ordered by character offset."""
    matches = [
        ConnectorMatch(connector=match.group(1).lower(), index=match.start())
        for match in _CONNECTOR_PATTERN.finditer(text)
    ]
    return matches
