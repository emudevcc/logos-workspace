"""Models for the Bíblia cockpit (pericope exegesis workflow).

Follows the study-output schema agreed with the user: six sections plus
guardrails, validated structurally so the LLM report is always uniform.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StudyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=1, max_length=200)
    translation: str = Field(default="", max_length=40)
    language: str = Field(default="", max_length=10)


class PassageRef(BaseModel):
    """Canonical, parsed reference to a pericope."""

    book_code: str
    book_name_pt: str
    chapter: int
    start_verse: int | None = None
    end_verse: int | None = None
    display: str
    translation: str


class PassageText(BaseModel):
    ref: PassageRef
    passage_text: str
    copyright: str = ""


class LexicalItem(BaseModel):
    """One pivotal original-language word with parsing and consensus note."""

    term: str
    transliteration: str = ""
    lemma: str = ""
    parsing: str = ""
    contextual_definition: str = ""
    consensus_note: str = ""


class TextLiterary(BaseModel):
    genre: str
    authorial_tone: str
    unit_division: str


class HistoricalGrammatical(BaseModel):
    author: str
    recipients: str
    date: str
    geopolitical_context: str
    occasion: str


class RedemptiveTheological(BaseModel):
    placement_redemptive_history: str
    cross_references: list[str] = Field(default_factory=list)
    christological_significance: str


class PracticalApplication(BaseModel):
    action_items: list[str] = Field(default_factory=list)
    reflection_prompts: list[str] = Field(default_factory=list)
    obedience_areas: list[str] = Field(default_factory=list)


class BibleStudy(BaseModel):
    """The six-section exegesis report (user spec §2).

    The echo fields (reference/translation/passage_text) are filled by the
    backend from authoritative sources, so they are not LLM-required.
    """

    reference: str = ""
    translation: str = ""
    passage_text: str = ""
    text_literary: TextLiterary
    historical_grammatical: HistoricalGrammatical
    lexical_exegesis: list[LexicalItem] = Field(default_factory=list, max_length=3)
    redemptive_theological: RedemptiveTheological
    core_principle: str
    practical_application: PracticalApplication
    guardrail_notes: str = ""


class StudySummary(BaseModel):
    id: int
    reference: str
    translation: str
    book_code: str
    created_at: str


class StudyRecord(StudySummary):
    passage_text: str
    report: BibleStudy


class BookProfile(BaseModel):
    code: str
    name_pt: str
    testament: str
    genre: str
    author: str
    date: str
    occasion: str


class TranslationInfo(BaseModel):
    id: str
    abbreviation: str
    name: str
    language: str


class BiblePrefs(BaseModel):
    """Configured translation labels per UI language (es/en/pt)."""

    es: str
    en: str
    pt: str
