"""Unit tests for Word-of-Day rotation, curated entries, and the generator."""

from datetime import date

from app.services.word_of_day import ENTRY_COUNT, WordOfDayGenerator, entry_for_date, random_entry
from tests.backend.helpers import FakeLLM


def test_same_date_returns_same_entry() -> None:
    assert entry_for_date(date(2024, 1, 1)) == entry_for_date(date(2024, 1, 1))


def test_consecutive_dates_differ() -> None:
    assert (
        entry_for_date(date(2024, 1, 1)).expression != entry_for_date(date(2024, 1, 2)).expression
    )


def test_rotation_wraps_around() -> None:
    first = entry_for_date(date(2024, 1, 1))
    after_cycle = entry_for_date(date.fromordinal(date(2024, 1, 1).toordinal() + ENTRY_COUNT))
    assert first.expression == after_cycle.expression
    assert first.definition == after_cycle.definition


def test_every_entry_is_valid() -> None:
    for i in range(ENTRY_COUNT):
        entry = entry_for_date(date.fromordinal(i + 1))
        assert entry.expression
        assert entry.ipa.startswith("/")
        assert entry.register_tag
        assert entry.definition
        assert len(entry.examples) == 2
        assert entry.kind in {"idiom", "phrasal_verb", "collocation"}


def test_random_entry_is_valid() -> None:
    entry = random_entry()
    assert entry.expression
    assert entry.ipa.startswith("/")
    assert entry.register_tag
    assert entry.definition
    assert len(entry.examples) == 2
    assert entry.kind in {"idiom", "phrasal_verb", "collocation"}


def test_random_entry_avoids_immediate_repeat() -> None:
    first = random_entry()
    second = random_entry()
    assert first.expression != second.expression


async def test_generator_serves_llm_word_without_level_labels() -> None:
    llm = FakeLLM(
        result={
            "expression": "to turn on",
            "kind": "phrasal_verb",
            "ipa": "/tɜːn ɒn/",
            "register_tag": "Everyday",
            "definition": "To switch something on.",
            "examples": ["Please turn on the light.", "Turn on the TV after dinner."],
        }
    )
    result = await WordOfDayGenerator(llm).generate()
    assert result.expression == "to turn on"
    assert len(result.examples) == 2
    # The blend guidance is baked into the prompt; no user-facing level label.
    assert "Calibration:" in llm.calls[0]["system"]
    assert "Level" not in llm.calls[0]["system"]


async def test_generator_avoids_recent_items_in_prompt() -> None:
    llm = FakeLLM(
        result={
            "expression": "to keep the lights on",
            "kind": "collocation",
            "register_tag": "Everyday",
            "definition": "To maintain basic operations.",
            "examples": ["We just need to keep the lights on."],
        }
    )
    generator = WordOfDayGenerator(llm)
    await generator.generate()
    await generator.generate()
    second_user = llm.calls[1]["user"]
    assert "to keep the lights on" in second_user
