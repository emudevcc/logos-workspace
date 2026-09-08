"""Executive De-Clutter & Polish Assistant."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.assist import DeclutterRequest, DeclutterResult, VerbUpgrade
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are an executive writing coach. Rewrite the draft to cut 30-40% of filler "
    "phrases while preserving meaning and tone. List the filler phrases you removed and "
    "weak-to-strong verb upgrades (e.g. 'take into consideration' -> 'evaluate'). Assess "
    "the executive tone in one sentence. Respond ONLY with JSON shaped exactly like: "
    '{"revised": "string", "cut_phrases": ["string"], '
    '"verb_upgrades": [{"weak": "string", "strong": "string"}], "tone": "string"}.'
)


class _LLMVerbUpgrade(BaseModel):
    weak: str
    strong: str


class _DeclutterLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revised: str
    cut_phrases: list[str] = Field(default_factory=list)
    verb_upgrades: list[_LLMVerbUpgrade] = Field(default_factory=list)
    tone: str


class DeclutterService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def declutter(self, request: DeclutterRequest) -> DeclutterResult:
        raw = await self._llm.complete_json(system=_SYSTEM, user=request.draft, max_tokens=800)
        try:
            parsed = _DeclutterLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Declutter validation failed: {exc}") from exc

        before = _word_count(request.draft)
        after = _word_count(parsed.revised)
        reduction = round((before - after) / before * 100, 1) if before else 0.0

        return DeclutterResult(
            word_count_before=before,
            word_count_after=after,
            reduction_pct=max(0.0, reduction),
            revised=parsed.revised,
            cut_phrases=parsed.cut_phrases,
            verb_upgrades=[
                VerbUpgrade(weak=item.weak, strong=item.strong) for item in parsed.verb_upgrades
            ],
            tone_assessment=parsed.tone,
        )


def _word_count(text: str) -> int:
    return len(text.split())
