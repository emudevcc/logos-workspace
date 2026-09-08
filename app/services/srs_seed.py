"""Idempotent seeding of the default spaced-repetition deck."""

from __future__ import annotations

import json

from app.core.db import Database
from app.core.timeutil import iso_utc, utc_now

DEFAULT_DECK_SLUG = "workplace"
DEFAULT_DECK_NAME = "Workplace English"
DEFAULT_DECK_DESCRIPTION = (
    "Idioms, phrasal verbs, and technical collocations for professional communication."
)

_CARDS: tuple[tuple[str, str, str, str, list[str]], ...] = (
    (
        "to move the needle",
        "To produce a noticeable effect or meaningful change.",
        "/muːv ðə ˈniːdəl/",
        "Executive",
        [
            "That refactor barely moved the needle on latency.",
            "We need features that move the needle for enterprise clients.",
        ],
    ),
    (
        "to push back (on)",
        "To resist or raise an objection to a request or proposal.",
        "/pʊʃ bæk/",
        "Professional",
        [
            "She pushed back on the unrealistic deadline.",
            "Don't hesitate to push back if the scope creeps.",
        ],
    ),
    (
        "bandwidth",
        "Available time, attention, or mental capacity to take on work.",
        "/ˈbændwɪdθ/",
        "Executive",
        [
            "I don't have the bandwidth for another project this sprint.",
            "Let me check my team's bandwidth before committing.",
        ],
    ),
    (
        "low-hanging fruit",
        "Tasks or wins that yield quick results with relatively little effort.",
        "/ləʊ ˈhæŋɪŋ fruːt/",
        "Professional",
        [
            "Let's tackle the low-hanging fruit before the rewrite.",
            "Tightening the checkout copy is low-hanging fruit.",
        ],
    ),
    (
        "to be on the same page",
        "To share the same understanding or level of agreement.",
        "/ɒn ðə seɪm peɪdʒ/",
        "Professional",
        [
            "Let's align with legal to make sure we're on the same page.",
            "The kickoff got the whole squad on the same page.",
        ],
    ),
    (
        "to boil the ocean",
        "To attempt something impossibly broad or over-scoped.",
        "/bɔɪl ði ˈəʊʃn/",
        "Executive",
        [
            "Don't boil the ocean — limit the pilot to one market.",
            "The proposal tries to boil the ocean.",
        ],
    ),
    (
        "to move the goalposts",
        "To change the criteria or target after work has already begun.",
        "/muːv ðə ˈɡəʊlpəʊsts/",
        "Professional",
        [
            "Adding acceptance criteria now is moving the goalposts.",
            "We can't keep moving the goalposts on what 'done' means.",
        ],
    ),
    (
        "runway",
        "The amount of time or funding remaining before a limit is reached.",
        "/ˈrʌnweɪ/",
        "Executive",
        [
            "We have six months of runway at this burn rate.",
            "The roadmap gives the team enough runway.",
        ],
    ),
    (
        "to get buy-in",
        "To secure agreement and active support from stakeholders.",
        "/ɡet ˈbaɪ ɪn/",
        "Executive",
        [
            "We need buy-in from finance before launch.",
            "Getting buy-in early prevents expensive rework.",
        ],
    ),
    (
        "to circle back",
        "To return to a topic or person later, usually with new information.",
        "/ˈsɜːkl bæk/",
        "Executive",
        [
            "I'll circle back with you after the numbers come in.",
            "Let's circle back to pricing on Friday.",
        ],
    ),
    (
        "to drill down (into)",
        "To examine something in greater detail.",
        "/drɪl daʊn/",
        "Professional",
        [
            "Let's drill down into the error logs.",
            "The analyst drilled down into cohort retention.",
        ],
    ),
    (
        "actionable insights",
        "Findings that are specific enough to act on directly.",
        "/ˈækʃənəbl ˈɪnsaɪts/",
        "Executive",
        [
            "The report turns raw data into actionable insights.",
            "Give me three actionable insights from the survey.",
        ],
    ),
)


async def seed_default_deck(db: Database) -> None:
    """Insert the default deck and cards once; a no-op if it already exists."""
    cursor = await db.connection.execute(
        "SELECT id FROM decks WHERE slug = ?", (DEFAULT_DECK_SLUG,)
    )
    existing = await cursor.fetchone()
    if existing is not None:
        return

    due_at = iso_utc(utc_now())
    async with db.transaction() as conn:
        cursor = await conn.execute(
            "INSERT INTO decks (slug, name, description) VALUES (?, ?, ?)",
            (DEFAULT_DECK_SLUG, DEFAULT_DECK_NAME, DEFAULT_DECK_DESCRIPTION),
        )
        deck_id = cursor.lastrowid
        for front, back, ipa, register, examples in _CARDS:
            await conn.execute(
                "INSERT INTO cards "
                "(deck_id, front, back, ipa, register_tag, examples, due_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (deck_id, front, back, ipa, register, json.dumps(examples), due_at),
            )
