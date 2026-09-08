"""Spanish Scripture text retrieval via API.Bible (api.scripture.api.bible).

The provider resolves a translation label (default from config, e.g. RVR09 or
RVR60 when a source offers it) against the API.Bible Spanish catalog and
fetches pericope text with ``content-type=text``. Fetched passages are cached
in SQLite so the online service is only hit when a passage is new or stale.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx

from app.core.cache import TTLCache
from app.core.db import Database
from app.core.timeutil import iso_utc, utc_now
from app.schemas.bible import PassageRef

logger = logging.getLogger(__name__)

_CATALOG_TTL_SECONDS = 24 * 3600.0


class BibleNotConfiguredError(RuntimeError):
    """Raised when a Bible call is attempted without an API key."""


class BibleUpstreamError(RuntimeError):
    """Raised when API.Bible returns an unusable response."""


class BibleTranslationUnavailableError(BibleUpstreamError):
    """Raised when the requested translation is not in the Spanish catalog."""


class BibleDbCache:
    """SQLite-backed cache of fetched passages, keyed by (bible_id, passage_id)."""

    def __init__(self, db: Database, ttl_seconds: float) -> None:
        self._db = db
        self._ttl = ttl_seconds

    async def get(self, bible_id: str, passage_id: str) -> str | None:
        cutoff = iso_utc(utc_now() - timedelta(seconds=self._ttl))
        cursor = await self._db.connection.execute(
            "SELECT content FROM bible_cache "
            "WHERE bible_id = ? AND passage_id = ? AND fetched_at >= ?",
            (bible_id, passage_id, cutoff),
        )
        row = await cursor.fetchone()
        return str(row["content"]) if row is not None else None

    async def put(self, bible_id: str, passage_id: str, content: str) -> None:
        async with self._db.transaction() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO bible_cache (bible_id, passage_id, content) "
                "VALUES (?, ?, ?)",
                (bible_id, passage_id, content),
            )


def _key(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def passage_id_for(ref: PassageRef) -> str:
    """Build the API.Bible passage id (whole chapter, verse, or verse range)."""
    base = f"{ref.book_code}.{ref.chapter}"
    if ref.start_verse is None:
        return base
    if ref.end_verse is None or ref.end_verse == ref.start_verse:
        return f"{base}.{ref.start_verse}"
    return f"{base}.{ref.start_verse}-{ref.book_code}.{ref.chapter}.{ref.end_verse}"


class BibleTextProvider:
    """API.Bible text provider with catalog resolution and passage caching."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        api_key: str,
        default_translation: str,
        cache: BibleDbCache | None = None,
        catalog_ttl_seconds: float = _CATALOG_TTL_SECONDS,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_translation = default_translation
        self._cache = cache
        self._catalog: TTLCache[list[tuple[str, str, str]]] = TTLCache(catalog_ttl_seconds)

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def resolve_bible_id(self, translation: str) -> str:
        label = (translation or "").strip() or self._default_translation
        wanted = _key(label)
        catalog = await self._catalog.get("spa", self._load_catalog)
        for bible_id, abbreviation, name in catalog:
            if _key(abbreviation) == wanted or _key(name) == wanted:
                return bible_id
        available = ", ".join(f"{abbreviation} ({name})" for _, abbreviation, name in catalog[:8])
        raise BibleTranslationUnavailableError(
            f"A tradução '{label}' não está disponível no catálogo espanhol da API.Bible. "
            f"Disponíveis (exemplo): {available}."
        )

    async def fetch_text(self, ref: PassageRef, translation: str = "") -> str:
        """Return the plain text for a parsed pericope (cached when possible)."""
        if not self.enabled:
            raise BibleNotConfiguredError("Bible API key is not configured")
        bible_id = await self.resolve_bible_id(translation or self._default_translation)
        passage_id = passage_id_for(ref)

        if self._cache is not None:
            cached = await self._cache.get(bible_id, passage_id)
            if cached is not None:
                return cached

        content = await self._remote(bible_id, passage_id)
        if self._cache is not None:
            await self._cache.put(bible_id, passage_id, content)
        return content

    async def _load_catalog(self) -> list[tuple[str, str, str]]:
        response = await self._client.get(
            f"{self._base_url}/bibles",
            params={"language": "spa"},
            headers={"api-key": self._api_key},
            timeout=20.0,
        )
        if response.status_code != 200:
            raise BibleUpstreamError(f"API.Bible catalog request failed ({response.status_code})")
        try:
            entries = response.json().get("data", [])
        except ValueError as exc:  # pragma: no cover - defensive
            raise BibleUpstreamError("API.Bible returned invalid JSON for the catalog") from exc
        catalog: list[tuple[str, str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            catalog.append(
                (
                    str(entry["id"]),
                    str(entry.get("abbreviation") or ""),
                    str(entry.get("name") or ""),
                )
            )
        return catalog

    async def _remote(self, bible_id: str, passage_id: str) -> str:
        url = f"{self._base_url}/bibles/{bible_id}/passages/{passage_id}"
        try:
            response = await self._client.get(
                url,
                params={"content-type": "text"},
                headers={"api-key": self._api_key},
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise BibleUpstreamError(f"API.Bible passage request failed: {exc}") from exc
        if response.status_code != 200:
            raise BibleUpstreamError(
                f"API.Bible passage request failed ({response.status_code}) for {passage_id}"
            )
        try:
            data = response.json().get("data") or {}
            content = data.get("content")
        except ValueError as exc:  # pragma: no cover - defensive
            raise BibleUpstreamError("API.Bible returned invalid JSON for the passage") from exc
        if not isinstance(content, str) or not content.strip():
            raise BibleUpstreamError(f"API.Bible returned no text for {passage_id}")
        return content
