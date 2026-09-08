"""Models for the Rapid-Fire PREP drill."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PrepScenario(BaseModel):
    id: str
    context: str
    task: str


class PrepEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(min_length=1, max_length=2000)
    response: str = Field(min_length=1, max_length=20000)
    elapsed_seconds: int = Field(default=90, ge=0, le=300)


class PrepFeedback(BaseModel):
    conciseness_score: int
    conciseness_feedback: str
    structure_score: int
    structure_feedback: str
    bluf_rewrite: str
    overall_feedback: str
