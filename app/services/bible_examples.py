"""LLM-generated example-passage suggestions for the Bíblia cockpit.

The cockpit shows a row of clickable example-passage chips above the study
input. Those used to be a fixed, hardcoded list per language; this service asks
the shared LLM for a fresh set on demand, mirroring the shape of
``WordOfDayGenerator`` (generate via ``complete_json``, keep a small
recent-window so consecutive loads differ, raise ``LLMError`` on failure and let
the caller decide what "no output" means).

One deliberate divergence from Word-of-Day: a passage *reference* is validated
through the real parser before it is ever returned. A vague vocabulary item is
harmless, but a hallucinated book name or a malformed reference either 422s when
clicked or — worse — sends a slightly-wrong passage into the study pipeline. So
anything ``parse_reference`` rejects is dropped silently rather than shown.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.bible_parser import BibleReferenceError, parse_reference
from app.services.llm import LLMError, LLMProvider

_SUGGEST_COUNT = 6
# Small window per language: enough to stop immediate repeats across reloads
# without starving the model of well-known passages to choose from.
_RECENT_WINDOW = 6

_SYSTEM_BY_LANG = {
    "es": (
        "Eres un curador bíblico. Propón pasajes conocidos y aptos para un estudio "
        f"exegético de 5 a 15 versículos. Devuelve EXACTAMENTE {_SUGGEST_COUNT} "
        "referencias variadas, en español (p. ej. 'Romanos 8:31-39'): mezcla Antiguo "
        "y Nuevo Testamento y no repitas el mismo libro dos veces. Responde SOLO con "
        'JSON: {"passages": ["string"]}.'
    ),
    "en": (
        "You are a Bible curator. Suggest well-known passages suited to a 5-15 verse "
        f"exegetical study. Return EXACTLY {_SUGGEST_COUNT} varied references in "
        "English (e.g. 'Romans 8:31-39'): mix Old and New Testament and do not repeat "
        'the same book twice. Respond ONLY with JSON: {"passages": ["string"]}.'
    ),
    "pt": (
        "Você é um curador bíblico. Sugira passagens conhecidas e adequadas para um "
        f"estudo exegético de 5 a 15 versículos. Devolva EXATAMENTE {_SUGGEST_COUNT} "
        "referências variadas em português (p. ex. 'Romanos 8:31-39'): misture Antigo "
        "e Novo Testamento e não repita o mesmo livro duas vezes. Responda APENAS com "
        'JSON: {"passages": ["string"]}.'
    ),
}


_AVOID_PLACEHOLDER = {
    "es": "Evita repetir estas referencias recientes: ",
    "en": "Avoid reusing these recent references: ",
    "pt": "Evite repetir estas referências recentes: ",
}


class _SuggestedPassages(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # ``Any`` + explicit filtering below: a model that emits one non-string
    # entry among otherwise-good references should still yield those good ones.
    # Declaring ``list[str]`` would make Pydantic reject the whole response.
    passages: list[Any] = Field(default_factory=list)


class BiblePassageSuggester:
    """On-the-fly example-passage suggester backed by the shared LLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        # One window per language: the three chip sets are independent and
        # should not cross-suppress each other.
        self._recent: dict[str, deque[str]] = {}

    @property
    def enabled(self) -> bool:
        return self._llm.enabled

    async def suggest(self, language: str) -> list[str]:
        """Return valid passage references for ``language``.

        Raises ``LLMError`` on any generation failure — the caller decides
        whether that means an empty response. Never returns a string that
        ``parse_reference`` would reject.
        """
        window = self._recent.setdefault(language, deque(maxlen=_RECENT_WINDOW))
        avoid = _AVOID_PLACEHOLDER[language] + ", ".join(window) if window else ""

        raw = await self._llm.complete_json(
            system=_SYSTEM_BY_LANG[language],
            user=avoid,
            max_tokens=150,
            temperature=0.9,
        )
        try:
            candidates = _SuggestedPassages.model_validate(raw).passages
        except ValidationError as exc:
            raise LLMError(f"Bible passage suggestion validation failed: {exc}") from exc

        valid: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            try:
                parse_reference(candidate)
            except BibleReferenceError:
                # A suggestion the app itself cannot parse is worse than no
                # suggestion: drop it silently rather than show it.
                continue
            valid.append(candidate)

        for reference in valid:
            window.append(reference)
        return valid


def all_languages() -> tuple[str, str, str]:
    """The languages this suggester has prompts for."""
    return ("es", "en", "pt")
