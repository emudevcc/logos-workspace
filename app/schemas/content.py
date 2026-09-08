"""Response models for the content endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class VocabTerm(BaseModel):
    term: str
    definition: str


class Headline(BaseModel):
    source: str
    title: str
    link: str
    published: str | None = None
    vocab: list[VocabTerm] = Field(default_factory=list)


class NewsPulse(BaseModel):
    headlines: list[Headline]


class WordOfDay(BaseModel):
    date: date
    expression: str
    kind: Literal["idiom", "phrasal_verb", "collocation"]
    ipa: str
    register_tag: str
    definition: str
    examples: list[str]


class WordEntry(BaseModel):
    expression: str
    kind: str
    register_tag: str


class PodcastEpisode(BaseModel):
    title: str
    link: str
    published: str | None = None
    summary: str | None = None
    audio_url: str | None = None


class PodcastDigest(BaseModel):
    title: str
    brief: list[str]
    key_terms: list[VocabTerm] = Field(default_factory=list)
    episodes: list[PodcastEpisode]


class DictionaryLookup(BaseModel):
    word: str
    ipa: str
    part_of_speech: str = ""
    synonyms: list[str] = Field(default_factory=list)
    spanish: str
    example: str = ""
