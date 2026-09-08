"""SQLite persistence layer built on a single shared ``aiosqlite`` connection.

The Raspberry Pi 3B has 1 GB of RAM and a slow SD card, so the backend keeps
exactly one connection for the whole process lifetime and serializes writes
with an ``asyncio.Lock``. WAL mode lets readers proceed while a writer commits.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id       INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    front         TEXT    NOT NULL,
    back          TEXT    NOT NULL,
    ipa           TEXT    NOT NULL DEFAULT '',
    register_tag  TEXT    NOT NULL DEFAULT '',
    examples      TEXT    NOT NULL DEFAULT '[]',
    ease_factor   REAL    NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id            INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    grade              INTEGER NOT NULL,
    quality            INTEGER NOT NULL,
    ease_factor_before REAL    NOT NULL,
    ease_factor_after  REAL    NOT NULL,
    interval_before    INTEGER NOT NULL,
    interval_after     INTEGER NOT NULL,
    reviewed_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cards_deck_due ON cards(deck_id, due_at);
CREATE INDEX IF NOT EXISTS idx_reviews_card ON reviews(card_id);
"""

# Baseline schema is version 1. Future schema changes append a migration script
# here; each is applied in order based on PRAGMA user_version.
MIGRATIONS: tuple[str, ...] = ()


class Database:
    """Wraps one ``aiosqlite`` connection with explicit write transactions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    @property
    def path(self) -> Path:
        return self._path

    async def connect(self) -> None:
        if self._conn is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None puts SQLite in autocommit mode; transactions are
        # then managed explicitly inside ``transaction()`` via BEGIN IMMEDIATE.
        self._conn = await aiosqlite.connect(self._path, isolation_level=None)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA synchronous = NORMAL")
        await self._conn.execute("PRAGMA busy_timeout = 5000")
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.commit()

    async def initialize(self) -> None:
        conn = self._require_connection()
        await conn.executescript(_SCHEMA_SQL)
        await self._apply_migrations(conn)
        await conn.commit()

    async def _apply_migrations(self, conn: aiosqlite.Connection) -> None:
        version = await self._user_version(conn)
        if version == 0:
            version = 1
            await conn.execute("PRAGMA user_version = 1")
        for target, migration in enumerate(MIGRATIONS, start=2):
            if version < target:
                await conn.executescript(migration)
                await conn.execute(f"PRAGMA user_version = {target}")

    async def _user_version(self, conn: aiosqlite.Connection) -> int:
        cursor = await conn.execute("PRAGMA user_version")
        row = await cursor.fetchone()
        return int(row[0]) if row is not None else 0

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def connection(self) -> aiosqlite.Connection:
        return self._require_connection()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Run a serialized write transaction, committing or rolling back as a unit.

        ``BEGIN IMMEDIATE`` grabs the write lock up front, which avoids
        ``SQLITE_BUSY`` upgrade deadlocks under WAL concurrency.
        """
        conn = self._require_connection()
        async with self._write_lock:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                await conn.commit()
            except BaseException:
                await conn.rollback()
                raise

    def _require_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected; call connect() first.")
        return self._conn
