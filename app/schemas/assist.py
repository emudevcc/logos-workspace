"""Models for the de-clutter, voice, radio, and speech endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeclutterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: str = Field(min_length=1, max_length=20000)


class VerbUpgrade(BaseModel):
    weak: str
    strong: str


class DeclutterResult(BaseModel):
    word_count_before: int
    word_count_after: int
    reduction_pct: float
    revised: str
    cut_phrases: list[str] = Field(default_factory=list)
    verb_upgrades: list[VerbUpgrade] = Field(default_factory=list)
    tone_assessment: str


class Turn(BaseModel):
    role: Literal["user", "partner"]
    text: str = Field(min_length=1, max_length=4000)


class VoiceTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(min_length=1, max_length=2000)
    user_says: str = Field(min_length=1, max_length=4000)
    history: list[Turn] = Field(default_factory=list)


class VoiceTurnResponse(BaseModel):
    partner_says: str
    follow_up_hint: str = ""


class RadioStation(BaseModel):
    id: str
    name: str
    stream_url: str
    format: Literal["mp3", "aac"]


class TranscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_url: str = Field(min_length=1, max_length=2048)

    @field_validator("audio_url")
    @classmethod
    def _http_scheme_only(cls, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("audio_url must use http or https")
        return value


class ConnectorHighlight(BaseModel):
    connector: str
    index: int


class Transcript(BaseModel):
    text: str
    highlights: list[ConnectorHighlight] = Field(default_factory=list)


class QuizRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)


class QuizItem(BaseModel):
    question: str
    correct_answer: str
    distractors: list[str]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    register_tag: Literal[
        "Executive", "Informal", "Technical", "Polite", "Hedged"
    ] = "Executive"


class RegisterResult(BaseModel):
    rewritten: str


class CorrectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: str = Field(min_length=1, max_length=20000)


class Correction(BaseModel):
    original: str
    corrected: str
    explanation: str = ""


class CorrectResult(BaseModel):
    corrected: str
    corrections: list[Correction] = Field(default_factory=list)
    error_count: int = 0


class MonologueEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1, max_length=2000)
    transcript: str = Field(min_length=1, max_length=20000)
    duration_seconds: float = Field(default=0.0, ge=0.0)


class MonologueFeedback(BaseModel):
    structure_score: int
    fluency_score: int
    vocabulary_score: int
    grammar_score: int
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    model_answer: str = ""
