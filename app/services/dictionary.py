"""Click/select-to-translate dictionary lookup via the LLM.

Accepts a single word or a short phrase (phrasal verb, collocation, sentence).
Each term is cached per-process for a day (keyed case-insensitively) so repeat
lookups are instant and free.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.cache import TTLCache
from app.schemas.content import DictionaryLookup
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are an English dictionary for a Spanish-speaking learner. Given a word OR "
    "phrase (a phrasal verb, collocation, or short sentence), return its IPA "
    "pronunciation, part of speech (use 'phrase' for multi-word items), up to 4 "
    "synonyms (may be empty for phrases), the Spanish translation, and one short "
    'example. Respond ONLY with JSON: {"ipa": "string", "part_of_speech": '
    '"string", "synonyms": ["string"], "spanish": "string", "example": "string"}.'
)


class _Lookup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ipa: str
    part_of_speech: str = ""
    synonyms: list[str] = Field(default_factory=list)
    spanish: str
    example: str = ""


class DictionaryService:
    def __init__(self, llm: LLMProvider, ttl_seconds: float = 86400.0) -> None:
        self._llm = llm
        self._cache = TTLCache[DictionaryLookup](ttl_seconds)

    async def lookup(self, word: str) -> DictionaryLookup:
        term = word.strip()
        return await self._cache.get(term.lower(), lambda: self._fetch(term))

    async def _fetch(self, term: str) -> DictionaryLookup:
        raw = await self._llm.complete_json(system=_SYSTEM, user=term, max_tokens=250)
        try:
            parsed = _Lookup.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Dictionary lookup validation failed: {exc}") from exc
        return DictionaryLookup(
            word=term,
            ipa=parsed.ipa,
            part_of_speech=parsed.part_of_speech,
            synonyms=parsed.synonyms[:4],
            spanish=parsed.spanish,
            example=parsed.example,
        )
