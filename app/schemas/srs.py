"""Models for the spaced-repetition API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeckOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    due_count: int = 0


class CardOut(BaseModel):
    id: int
    deck_id: int
    front: str
    back: str
    ipa: str = ""
    register_tag: str = ""
    examples: list[str] = Field(default_factory=list)
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: int = Field(gt=0)
    grade: Literal[1, 2, 3, 4]


class ReviewResponse(BaseModel):
    card_id: int
    grade: int
    quality: int
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: str


class CardCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deck_id: int | None = Field(default=None, gt=0)
    front: str = Field(min_length=1, max_length=500)
    back: str = Field(min_length=1, max_length=2000)
    ipa: str = Field(default="", max_length=200)
    register_tag: str = Field(default="", max_length=100)
    examples: list[str] = Field(default_factory=list)


class Stats(BaseModel):
    cards_due: int
    cards_new: int
    cards_total: int
    reviews_today: int
    streak_days: int
    daily_goal: int = 20


class SrsExport(BaseModel):
    decks: list[DeckOut]
    cards: list[CardOut]
