"""Models for the Português cockpit (PT-BR study features).

PT-BR study content is immersion-first: everything a learner sees is written in
Portuguese, while ``nota_es`` fields carry short Spanish scaffolding notes that
exploit the learner's native Spanish (false-friend alerts, transfer traps).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PtWordCategory = Literal["palavra", "expressao", "colocacao"]


class PtWordOfDay(BaseModel):
    date: date
    expression: str
    category: PtWordCategory
    definition_pt: str
    nota_es: str = ""
    examples: list[str] = Field(default_factory=list)


class PtGrammarRule(BaseModel):
    title: str
    regra_pt: str
    nota_es: str = ""
    exemplo_ok: str
    exemplo_err: str | None = None


class PtGrammarCoachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pergunta: str = Field(min_length=1, max_length=1000)


class PtGrammarCoachResult(BaseModel):
    resposta_pt: str
    nota_es: str = ""
    exemplos: list[str] = Field(default_factory=list)


class PtMinimalPair(BaseModel):
    a: str
    b: str
    nota_es: str


class PtPitfall(BaseModel):
    issue: str
    tip_pt: str
    nota_es: str = ""


class PtSentence(BaseModel):
    frase: str
    nota_es: str = ""
    dica: str = ""


class PtHeadline(BaseModel):
    title: str
    source: str
    url: str


class PtNewsPulse(BaseModel):
    headlines: list[PtHeadline]
