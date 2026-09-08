"""Tests for the aiosqlite-backed Database layer."""

import aiosqlite
import pytest

from app.core.db import Database


async def test_initialize_creates_schema(database: Database) -> None:
    cursor = await database.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in await cursor.fetchall()}
    assert {"decks", "cards", "reviews"} <= tables


async def test_wal_mode_is_enabled(database: Database) -> None:
    cursor = await database.connection.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0].lower() == "wal"


async def test_foreign_keys_are_enforced(database: Database) -> None:
    with pytest.raises(aiosqlite.IntegrityError):
        await database.connection.execute(
            "INSERT INTO cards (deck_id, front, back, due_at) "
            "VALUES (999, 'a', 'b', '2024-01-01T00:00:00+00:00')"
        )


async def test_transaction_commits_on_success(database: Database) -> None:
    async with database.transaction() as conn:
        await conn.execute("INSERT INTO decks (slug, name) VALUES ('tech', 'Tech')")
    cursor = await database.connection.execute("SELECT name FROM decks WHERE slug = 'tech'")
    row = await cursor.fetchone()
    assert row is not None
    assert row["name"] == "Tech"


async def test_transaction_rolls_back_on_error(database: Database) -> None:
    with pytest.raises(aiosqlite.IntegrityError):
        async with database.transaction() as conn:
            await conn.execute("INSERT INTO decks (slug, name) VALUES ('dupe', 'One')")
            await conn.execute("INSERT INTO decks (slug, name) VALUES ('dupe', 'Two')")
    cursor = await database.connection.execute("SELECT COUNT(*) FROM decks")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 0
