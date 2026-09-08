"""Models for the learning endpoints (verbs, pronunciation, grammar drills)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IrregularVerb(BaseModel):
    base: str
    past: str
    participle: str


class MinimalPair(BaseModel):
    a: str
    b: str
    ipa_a: str
    ipa_b: str


class Pitfall(BaseModel):
    issue: str
    tip: str


class ShadowSentence(BaseModel):
    sentence: str


DrillKind = Literal["phrasal_verb", "collocation", "use_of_english"]


class ClozeDrill(BaseModel):
    """A fill-the-gap multiple-choice drill (one blank, four options)."""

    sentence: str
    options: list[str]
    answer: str
    explanation: str = ""


class WordFormDrill(BaseModel):
    """A gap-fill requiring the correct derived form of a root word."""

    sentence: str
    root: str
    answer: str
    explanation: str = ""


class GrammarRule(BaseModel):
    id: str
    title: str
    rule: str
    examples: list[str]
    common_error: str


class GrammarCoachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)


class GrammarCoachResult(BaseModel):
    answer: str
