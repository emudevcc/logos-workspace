"""LLM-generated grammar drills (phrasal verbs, collocations, use of English,
word forms) and a free-form grammar coach.

Each drill is generated fresh on demand and calibrated to be *mostly elementary
(A1–A2) with an occasional clear intermediate (B1–B2)* — see ``difficulty.py``.
Drills are kept from repeating recently-served sentences; callers are
rate-limited and budgeted via the shared LLM client.
"""

from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.learning import (
    ClozeDrill,
    DrillKind,
    GrammarCoachResult,
    WordFormDrill,
)
from app.services.difficulty import calibration_guidance
from app.services.llm import LLMError, LLMProvider

_KIND_INSTRUCTION: dict[str, str] = {
    "phrasal_verb": (
        "a common English phrasal verb (e.g. 'to turn on', 'to look for')"
    ),
    "collocation": (
        "a common English collocation (e.g. 'make a decision', 'do the dishes')"
    ),
    "use_of_english": (
        "an everyday vocabulary or grammar item in a single gap (one word or "
        "short phrase from four options)"
    ),
}

_CLOZE_SYSTEM = (
    "You are an English drill generator for a Spanish-speaking beginner. "
    "Generate ONE multiple-choice fill-the-blank exercise about {instruction}. "
    "Write a realistic, SIMPLE sentence with a single blank shown as ___ , four "
    "options (only one correct), the correct answer exactly as written in "
    "options, and a one-sentence explanation in simple words. Respond ONLY with "
    "JSON: "
    '{{"sentence": "string with ___", "options": ["string", "string", "string", "string"], '
    '"answer": "string", "explanation": "string"}}.'
)

_WORD_FORM_SYSTEM = (
    "You are an English word-forms drill generator for a Spanish-speaking "
    "beginner. Generate ONE gap-fill where the learner must supply the correct "
    "derived form of a root word. The sentence must contain a single blank "
    "shown as ___ . Respond ONLY with "
    'JSON: {"sentence": "string with ___", "root": "string", "answer": "string", '
    '"explanation": "string"}'
    ".}"
)

_COACH_SYSTEM = (
    "You are an expert English grammar coach for a Spanish-speaking beginner. "
    "Answer the learner's question clearly and concisely in SIMPLE English, "
    "explain the rule, contrast it with common Spanish-speaker errors, and give "
    "one or two short examples. Respond "
    'ONLY with JSON: {"answer": "string"}.'
)

_RECENT_WINDOW = 6
_MAX_ATTEMPTS = 3


class _ClozeLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sentence: str
    options: list[str] = Field(default_factory=list)
    answer: str
    explanation: str = ""


class _WordFormLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sentence: str
    root: str
    answer: str
    explanation: str = ""


class _CoachLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer: str


def _normalize(sentence: str) -> str:
    """Case/whitespace/punctuation-insensitive key used to catch repeats."""
    return " ".join(sentence.lower().strip(" .!?,;:\"'").split())


class GrammarDrillService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._recent_cloze: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=_RECENT_WINDOW)
        )
        self._recent_word_forms: deque[str] = deque(maxlen=_RECENT_WINDOW)

    async def drill(self, kind: DrillKind) -> ClozeDrill:
        system = _CLOZE_SYSTEM.format(
            instruction=f"{_KIND_INSTRUCTION[kind]}. Calibration: {calibration_guidance()}"
        )
        recent = self._recent_cloze[kind]
        user = f"Drill kind: {kind}. Avoid repeating these recent sentences: {list(recent)}."

        drill: ClozeDrill | None = None
        last_valid: ClozeDrill | None = None
        for _ in range(_MAX_ATTEMPTS):
            raw = await self._llm.complete_json(
                system=system, user=user, max_tokens=400, temperature=0.85
            )
            try:
                parsed = _ClozeLLM.model_validate(raw)
            except ValidationError as exc:
                raise LLMError(f"Grammar drill validation failed: {exc}") from exc
            options = parsed.options[:4]
            if parsed.answer not in options:
                # A fresh roll is cheaper than serving an unusable drill.
                continue
            candidate = ClozeDrill(
                sentence=parsed.sentence,
                options=options,
                answer=parsed.answer,
                explanation=parsed.explanation,
            )
            last_valid = candidate
            sentence_key = _normalize(parsed.sentence)
            if any(_normalize(seen) == sentence_key for seen in recent):
                continue
            drill = candidate
            break

        # Retries exist to dodge repeats; if the model insists on a duplicate we
        # still serve a structurally valid drill rather than erroring.
        drill = drill or last_valid
        if drill is None:
            raise LLMError("Grammar drill failed validation after retries")
        self._recent_cloze[kind].append(drill.sentence)
        return drill

    async def word_forms(self) -> WordFormDrill:
        system = (
            f"{_WORD_FORM_SYSTEM} Calibration: {calibration_guidance()} "
            "Avoid repeating phrasing from recent drills."
        )
        recent = self._recent_word_forms
        user = f"Recent sentences: {list(recent)}."

        drill: WordFormDrill | None = None
        last_valid: WordFormDrill | None = None
        for _ in range(_MAX_ATTEMPTS):
            raw = await self._llm.complete_json(
                system=system, user=user, max_tokens=400, temperature=0.85
            )
            try:
                parsed = _WordFormLLM.model_validate(raw)
            except ValidationError as exc:
                raise LLMError(f"Word-forms drill validation failed: {exc}") from exc
            candidate = WordFormDrill(
                sentence=parsed.sentence,
                root=parsed.root,
                answer=parsed.answer,
                explanation=parsed.explanation,
            )
            last_valid = candidate
            sentence_key = _normalize(parsed.sentence)
            if any(_normalize(seen) == sentence_key for seen in recent):
                continue
            drill = candidate
            break

        drill = drill or last_valid
        if drill is None:
            raise LLMError("Word-forms drill failed validation after retries")
        self._recent_word_forms.append(drill.sentence)
        return drill

    async def coach(self, question: str) -> GrammarCoachResult:
        raw = await self._llm.complete_json(system=_COACH_SYSTEM, user=question, max_tokens=600)
        try:
            parsed = _CoachLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Grammar coach validation failed: {exc}") from exc
        return GrammarCoachResult(answer=parsed.answer)
