"""LLM-backed PT-BR generators: grammar coach and shadowing sentences.

Both degrade to curated content when the LLM is unavailable or returns an
unusable answer, so the Português cockpit always has something to study.
"""

from __future__ import annotations

import logging
import random
from collections import deque

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.pt import PtGrammarCoachResult, PtSentence
from app.services.llm import LLMError, LLMProvider
from app.services.pt_content import FALLBACK_SENTENCES

logger = logging.getLogger(__name__)

_COACH_SYSTEM = (
    "Você é um professor de português brasileiro (PT-BR) para um falante nativo "
    "de espanhol de nível intermediário/avançado. Responda à pergunta de "
    "gramática de forma curta e prática, sempre em português e com exemplos. Em "
    "nota_es, escreva 1-2 frases curtas em espanhol explicando como o ponto se "
    "transfere ou difere do espanhol. Responda SOMENTE com JSON: "
    '{"resposta_pt": "string", "nota_es": "string", "exemplos": ["string"]}.'
)


class _CoachResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resposta_pt: str = ""
    nota_es: str = ""
    exemplos: list[str] = Field(default_factory=list)


class PtGrammarCoach:
    """Grammar coach that answers a free-form PT-BR grammar question."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def answer(self, question: str) -> PtGrammarCoachResult:
        raw = await self._llm.complete_json(
            system=_COACH_SYSTEM, user=question, max_tokens=600, temperature=0.3
        )
        try:
            parsed = _CoachResult.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"PT grammar coach validation failed: {exc}") from exc
        if not parsed.resposta_pt:
            raise LLMError("PT grammar coach returned an empty answer")
        return PtGrammarCoachResult(
            resposta_pt=parsed.resposta_pt,
            nota_es=parsed.nota_es,
            exemplos=list(parsed.exemplos)[:3],
        )


_SENTENCE_SYSTEM = (
    "Você é um redator de material de pronúncia para um hispanofalante "
    "aprendendo português brasileiro (nível intermediário/avançado). Escreva "
    "UMA frase natural, curta e útil do dia a dia brasileiro. Em nota_es, dê "
    "uma dica em espanhol sobre vocabulário ou transferência; em dica, aponte "
    "um ponto de pronúncia da frase (nasal, redução de vogal, R forte etc.). "
    "Responda SOMENTE com JSON: "
    '{"frase": "string", "nota_es": "string", "dica": "string"}.'
)


class _SentenceJson(BaseModel):
    model_config = ConfigDict(extra="ignore")

    frase: str = ""
    nota_es: str = ""
    dica: str = ""


class PtPracticeSentence:
    """Practice-sentence generator with a deterministic curated fallback."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._recent: deque[str] = deque(maxlen=3)

    async def sentence(self) -> PtSentence:
        if not self._llm.enabled:
            return self._fallback()
        try:
            raw = await self._llm.complete_json(
                system=_SENTENCE_SYSTEM, user="", max_tokens=300, temperature=0.9
            )
            parsed = _SentenceJson.model_validate(raw)
        except (LLMError, ValidationError) as exc:
            logger.warning("PT practice sentence generation failed, falling back: %s", exc)
            return self._fallback()
        if not parsed.frase:
            return self._fallback()
        self._recent.append(parsed.frase)
        return PtSentence(frase=parsed.frase, nota_es=parsed.nota_es, dica=parsed.dica)

    def _fallback(self) -> PtSentence:
        pool = [s for s in FALLBACK_SENTENCES if s.frase not in self._recent]
        if not pool:
            pool = list(FALLBACK_SENTENCES)
        sentence = random.choice(pool)
        self._recent.append(sentence.frase)
        return sentence
