"""Curated Word & Idiom of the Day with deterministic daily rotation.

The dataset is a fixed, hand-curated list of advanced idioms, phrasal verbs,
and professional collocations. Selection is date-based (``date.toordinal()``),
so every day yields one stable entry without any external call or database hit.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.content import WordEntry, WordOfDay
from app.services.difficulty import calibration_guidance
from app.services.llm import LLMError, LLMProvider

Kind = Literal["idiom", "phrasal_verb", "collocation"]


@dataclass(frozen=True, slots=True)
class _Entry:
    expression: str
    kind: Kind
    ipa: str
    register_tag: str
    definition: str
    examples: tuple[str, str]


_ENTRIES: tuple[_Entry, ...] = (
    _Entry(
        "to move the needle",
        "idiom",
        "/muːv ðə ˈniːdəl/",
        "Executive",
        "To produce a noticeable effect or meaningful change.",
        (
            "That refactor barely moved the needle on request latency.",
            "We need initiatives that actually move the needle for enterprise clients.",
        ),
    ),
    _Entry(
        "to push back (on)",
        "phrasal_verb",
        "/pʊʃ bæk/",
        "Professional",
        "To resist or raise an objection to a request or proposal.",
        (
            "She pushed back on the unrealistic deadline in the planning meeting.",
            "Don't hesitate to push back if the requirements start to creep.",
        ),
    ),
    _Entry(
        "bandwidth",
        "collocation",
        "/ˈbændwɪdθ/",
        "Executive",
        "Available time, attention, or mental capacity to take on work.",
        (
            "I don't have the bandwidth for another initiative this sprint.",
            "Let me check my team's bandwidth before we commit to the launch date.",
        ),
    ),
    _Entry(
        "to get the ball rolling",
        "idiom",
        "/ɡet ðə bɔːl ˈrəʊlɪŋ/",
        "Informal",
        "To start an activity or process moving.",
        (
            "Let's get the ball rolling with a short kickoff call tomorrow.",
            "I'll circulate the agenda to get the ball rolling on the migration.",
        ),
    ),
    _Entry(
        "low-hanging fruit",
        "collocation",
        "/ləʊ ˈhæŋɪŋ fruːt/",
        "Professional",
        "Tasks or wins that yield quick results with relatively little effort.",
        (
            "Let's tackle the low-hanging fruit before the full redesign.",
            "Tightening the checkout copy is low-hanging fruit for conversion.",
        ),
    ),
    _Entry(
        "to be on the same page",
        "idiom",
        "/ɒn ðə seɪm peɪdʒ/",
        "Professional",
        "To share the same understanding or level of agreement.",
        (
            "Let's align with legal to make sure we're all on the same page.",
            "The kickoff got the whole squad on the same page about scope.",
        ),
    ),
    _Entry(
        "to walk (someone) through",
        "phrasal_verb",
        "/wɔːk θruː/",
        "Professional",
        "To explain something to someone step by step.",
        (
            "Could you walk me through the incident timeline once more?",
            "She walked the client through the entire migration plan.",
        ),
    ),
    _Entry(
        "to circle back",
        "collocation",
        "/ˈsɜːkl bæk/",
        "Executive",
        "To return to a topic or person later, usually with new information.",
        (
            "I'll circle back with you once the quarterly numbers come in.",
            "Let's circle back to the pricing discussion on Friday.",
        ),
    ),
    _Entry(
        "to boil the ocean",
        "idiom",
        "/bɔɪl ði ˈəʊʃn/",
        "Executive",
        "To attempt something impossibly broad or over-scoped.",
        (
            "Don't boil the ocean — limit the pilot to a single market.",
            "The proposal tries to boil the ocean by covering every edge case.",
        ),
    ),
    _Entry(
        "to flag (something)",
        "phrasal_verb",
        "/flæɡ/",
        "Professional",
        "To draw attention to a potential issue or risk.",
        (
            "I want to flag a dependency risk in the rollout plan.",
            "She flagged the duplicate charges for the finance team to review.",
        ),
    ),
    _Entry(
        "to surface (an issue)",
        "collocation",
        "/ˈsɜːfɪs/",
        "Professional",
        "To bring a problem or fact into view so it can be addressed.",
        (
            "The audit surfaced several gaps in our access controls.",
            "Please surface any blockers during the daily standup.",
        ),
    ),
    _Entry(
        "to be in the weeds",
        "idiom",
        "/ɪn ðə wiːdz/",
        "Informal",
        "To be overly focused on minor details and lose sight of the big picture.",
        (
            "We're getting in the weeds on button color — let's zoom out.",
            "The code review went in the weeds on a trivial naming debate.",
        ),
    ),
    _Entry(
        "actionable insights",
        "collocation",
        "/ˈækʃənəbl ˈɪnsaɪts/",
        "Executive",
        "Findings that are specific enough to act on directly.",
        (
            "The report turns raw telemetry into actionable insights.",
            "Give me three actionable insights from the customer survey.",
        ),
    ),
    _Entry(
        "to move the goalposts",
        "idiom",
        "/muːv ðə ˈɡəʊlpəʊsts/",
        "Professional",
        "To change the criteria or target after work has already begun.",
        (
            "Adding acceptance criteria now is effectively moving the goalposts.",
            "We can't keep moving the goalposts on what 'done' means.",
        ),
    ),
    _Entry(
        "to drill down (into)",
        "phrasal_verb",
        "/drɪl daʊn/",
        "Professional",
        "To examine something in greater detail.",
        (
            "Let's drill down into the error logs before the review.",
            "The analyst drilled down into cohort-level retention.",
        ),
    ),
    _Entry(
        "runway",
        "collocation",
        "/ˈrʌnweɪ/",
        "Executive",
        "The amount of time or funding remaining before a limit is reached.",
        (
            "We have about six months of runway at the current burn rate.",
            "The extended roadmap gives the team enough runway to ship properly.",
        ),
    ),
    _Entry(
        "to touch base",
        "phrasal_verb",
        "/tʌtʃ beɪs/",
        "Professional",
        "To make brief contact with someone to share an update.",
        (
            "Let's touch base after the demo to collect feedback.",
            "I'll touch base with engineering about the open ticket.",
        ),
    ),
    _Entry(
        "to scope out",
        "phrasal_verb",
        "/skəʊp aʊt/",
        "Informal",
        "To assess the size, effort, or feasibility of a task.",
        (
            "First, scope out the data-migration effort before we commit.",
            "We need to scope out the integration before sending a quote.",
        ),
    ),
    _Entry(
        "to get buy-in",
        "collocation",
        "/ɡet ˈbaɪ ɪn/",
        "Executive",
        "To secure agreement and active support from stakeholders.",
        (
            "We need buy-in from finance before we announce the change.",
            "Getting buy-in early prevents expensive rework later.",
        ),
    ),
    _Entry(
        "to keep (someone) in the loop",
        "idiom",
        "/kiːp ɪn ðə luːp/",
        "Professional",
        "To keep someone informed about ongoing developments.",
        (
            "Please keep me in the loop on the incident response.",
            "Keep legal in the loop on any contract wording changes.",
        ),
    ),
)


_RANDOM_HISTORY_SIZE = 4
_random_history: deque[_Entry] = deque(maxlen=_RANDOM_HISTORY_SIZE)

ENTRY_COUNT: int = len(_ENTRIES)


def list_entries() -> list[WordEntry]:
    """Return all curated entries for browsing the archive."""
    return [
        WordEntry(
            expression=entry.expression,
            kind=entry.kind,
            register_tag=entry.register_tag,
        )
        for entry in _ENTRIES
    ]


def entry_for_date(day: date) -> WordOfDay:
    """Return the stable Word-of-Day entry for ``day``."""
    entry = _ENTRIES[day.toordinal() % len(_ENTRIES)]
    return WordOfDay(
        date=day,
        expression=entry.expression,
        kind=entry.kind,
        ipa=entry.ipa,
        register_tag=entry.register_tag,
        definition=entry.definition,
        examples=list(entry.examples),
    )


def _pick_random_entry() -> _Entry:
    """Pick an entry that was not served by a recent random call (no repeats).

    When almost every entry is in the recent history the window gives up and
    falls back to the full pool so ``random_entry`` never blocks.
    """
    recent = {entry.expression for entry in _random_history}
    candidates = [entry for entry in _ENTRIES if entry.expression not in recent]
    if not candidates:
        candidates = list(_ENTRIES)
    entry = random.choice(candidates)
    _random_history.append(entry)
    return entry


def random_entry() -> WordOfDay:
    """Return a random curated entry (a fresh word on manual refresh)."""
    entry = _pick_random_entry()
    return WordOfDay(
        date=date.today(),
        expression=entry.expression,
        kind=entry.kind,
        ipa=entry.ipa,
        register_tag=entry.register_tag,
        definition=entry.definition,
        examples=list(entry.examples),
    )


# ── LLM-generated Word of the Day ────────────────────────────────────────────
# The card can produce an unlimited stream of vocabulary items on the fly: the
# provider generates a fresh expression per request, calibrated to be *mostly
# elementary (A1–A2) with an occasional clear intermediate (B1–B2)*, and a
# small recent window keeps the model from repeating phrasing it just served.

_WORD_SYSTEM = (
    "You are an English vocabulary curator for a Spanish-speaking beginner. "
    "Suggest ONE everyday expression — an idiom, phrasal verb, or useful "
    "phrase — the learner should study. Keep it SIMPLE and natural, and write "
    "the definition and both examples in equally simple English. Prefer a "
    "common, current expression. Respond ONLY with JSON: "
    '{"expression": "string", "kind": "idiom|phrasal_verb|collocation", '
    '"ipa": "string", "register_tag": "string", "definition": "string", '
    '"examples": ["string", "string"]}.'
)

_RECENT_WINDOW = 5
_AVOID_PLACEHOLDER = "Avoid reusing any of these recent items: "


class _GeneratedWord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    expression: str
    kind: Kind
    ipa: str = ""
    register_tag: str = ""
    definition: str = ""
    examples: list[str] = Field(default_factory=list)


class WordOfDayGenerator:
    """On-the-fly Word-of-the-Day generator backed by the shared LLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._recent: deque[str] = deque(maxlen=_RECENT_WINDOW)

    @property
    def enabled(self) -> bool:
        return self._llm.enabled

    async def generate(self) -> WordOfDay:
        system = f"{_WORD_SYSTEM} Calibration: {calibration_guidance()}"
        avoid = _AVOID_PLACEHOLDER + ", ".join(self._recent) if self._recent else ""

        raw = await self._llm.complete_json(
            system=system, user=avoid, max_tokens=300, temperature=0.95
        )
        try:
            parsed = _GeneratedWord.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Word-of-day generation validation failed: {exc}") from exc
        if not parsed.expression or not parsed.definition:
            raise LLMError("Word-of-day generation returned an empty item")

        self._recent.append(parsed.expression)
        examples = list(parsed.examples)[:2]
        if not examples:
            examples = [parsed.definition]
        return WordOfDay(
            date=date.today(),
            expression=parsed.expression,
            kind=parsed.kind,
            ipa=parsed.ipa,
            register_tag=parsed.register_tag,
            definition=parsed.definition,
            examples=examples,
        )
