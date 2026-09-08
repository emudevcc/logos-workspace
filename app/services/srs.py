"""Spaced-repetition persistence service.

Wraps the pure SM-2 engine with SQLite reads/writes. Reviews are applied inside
a single serialized transaction so card state and review history stay atomic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import aiosqlite

from app.core.db import Database
from app.core.timeutil import iso_utc, utc_now
from app.schemas.srs import (
    CardCreateRequest,
    CardOut,
    DeckOut,
    ReviewRequest,
    ReviewResponse,
    SrsExport,
    Stats,
)
from app.services.srs_engine import next_repetition


class SrsError(RuntimeError):
    """Raised when an SRS operation cannot be completed."""


class SrsService:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def list_decks(self, cockpit: str | None = None) -> list[DeckOut]:
        if cockpit is None:
            cursor = await self._db.connection.execute(
                "SELECT id, slug, name, description FROM decks ORDER BY id"
            )
        else:
            cursor = await self._db.connection.execute(
                "SELECT id, slug, name, description FROM decks "
                "WHERE cockpit = ? ORDER BY id",
                (cockpit,),
            )
        rows = await cursor.fetchall()
        decks: list[DeckOut] = []
        for row in rows:
            decks.append(
                DeckOut(
                    id=row["id"],
                    slug=row["slug"],
                    name=row["name"],
                    description=row["description"],
                    due_count=await self._due_count(row["id"]),
                )
            )
        return decks

    async def due_cards(self, deck_id: int, limit: int = 20) -> list[CardOut]:
        """Return review cards (already seen at least once) that are due.

        Every card returned is due right now, so the review queue is randomized
        instead of presented in a fixed order.
        """
        now = iso_utc(utc_now())
        cursor = await self._db.connection.execute(
            "SELECT * FROM cards WHERE deck_id = ? AND repetitions > 0 AND due_at <= ? "
            "ORDER BY RANDOM() LIMIT ?",
            (deck_id, now, limit),
        )
        rows = await cursor.fetchall()
        return [_card_out(row) for row in rows]

    async def new_cards(self, deck_id: int, limit: int = 10) -> list[CardOut]:
        """Return unseen cards (never reviewed) up to ``limit`` for introduction.

        New cards arrive in random order so a deck never feels like a fixed
        sequence.
        """
        cursor = await self._db.connection.execute(
            "SELECT * FROM cards WHERE deck_id = ? AND repetitions = 0 "
            "ORDER BY RANDOM() LIMIT ?",
            (deck_id, limit),
        )
        rows = await cursor.fetchall()
        return [_card_out(row) for row in rows]

    async def get_card(self, card_id: int) -> CardOut | None:
        cursor = await self._db.connection.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        row = await cursor.fetchone()
        return _card_out(row) if row is not None else None

    async def review(self, request: ReviewRequest) -> ReviewResponse:
        card_id = request.card_id
        async with self._db.transaction() as conn:
            cursor = await conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
            row = await cursor.fetchone()
            if row is None:
                raise SrsError(f"Card {card_id} not found")
            card = _card_out(row)

            outcome = next_repetition(
                ease_factor=card.ease_factor,
                interval_days=card.interval_days,
                repetitions=card.repetitions,
                grade=request.grade,
            )

            now = utc_now()
            due_at = iso_utc(now + timedelta(days=outcome.interval_days))
            now_iso = iso_utc(now)

            await conn.execute(
                "UPDATE cards "
                "SET ease_factor = ?, interval_days = ?, repetitions = ?, "
                "    due_at = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    outcome.ease_factor,
                    outcome.interval_days,
                    outcome.repetitions,
                    due_at,
                    now_iso,
                    card_id,
                ),
            )
            await conn.execute(
                "INSERT INTO reviews "
                "(card_id, grade, quality, ease_factor_before, ease_factor_after, "
                " interval_before, interval_after) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    card_id,
                    request.grade,
                    outcome.quality,
                    card.ease_factor,
                    outcome.ease_factor,
                    card.interval_days,
                    outcome.interval_days,
                ),
            )

            return ReviewResponse(
                card_id=card_id,
                grade=request.grade,
                quality=outcome.quality,
                ease_factor=outcome.ease_factor,
                interval_days=outcome.interval_days,
                repetitions=outcome.repetitions,
                due_at=due_at,
            )

    async def add_card(self, request: CardCreateRequest, cockpit: str | None = None) -> CardOut:
        deck_id = request.deck_id or await self._default_deck_id(cockpit)
        if deck_id is None:
            raise SrsError("No deck available")

        due_at = iso_utc(utc_now())
        async with self._db.transaction() as conn:
            cursor = await conn.execute("SELECT id FROM decks WHERE id = ?", (deck_id,))
            if await cursor.fetchone() is None:
                raise SrsError(f"Deck {deck_id} not found")
            cursor = await conn.execute(
                "INSERT INTO cards "
                "(deck_id, front, back, ipa, register_tag, l1_hint, examples, due_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    deck_id,
                    request.front,
                    request.back,
                    request.ipa,
                    request.register_tag,
                    request.l1_hint,
                    json.dumps(request.examples),
                    due_at,
                ),
            )
            card_id = cursor.lastrowid
            if card_id is None:
                raise SrsError("Failed to create card")

        card = await self.get_card(card_id)
        if card is None:
            raise SrsError("Failed to create card")
        return card

    async def export(self) -> SrsExport:
        decks = await self.list_decks()
        cursor = await self._db.connection.execute("SELECT * FROM cards ORDER BY id")
        cards = [_card_out(row) for row in await cursor.fetchall()]
        return SrsExport(decks=decks, cards=cards)

    async def stats(self, cockpit: str | None = None) -> Stats:
        now_iso = iso_utc(utc_now())
        day_start = iso_utc(datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0))

        scope, where, params = self._cockpit_scope(cockpit)
        cards_from = f"FROM cards c {scope}"
        reviews_from = f"FROM reviews r JOIN cards c ON c.id = r.card_id {scope}"
        # " AND " appends the cockpit filter to a WHERE clause; " WHERE " starts
        # the clause when there is no cockpit filter.
        cond = f"{where} AND" if where else " WHERE "

        total = await self._count(f"SELECT COUNT(*) AS n {cards_from}{where}", params)
        new = await self._count(
            f"SELECT COUNT(*) AS n {cards_from}{cond} c.repetitions = 0", params
        )
        due = await self._count(
            f"SELECT COUNT(*) AS n {cards_from}{cond} c.repetitions > 0 AND c.due_at <= ?",
            (*params, now_iso),
        )
        reviews_today = await self._count(
            f"SELECT COUNT(*) AS n {reviews_from}{cond} r.reviewed_at >= ?",
            (*params, day_start),
        )

        return Stats(
            cards_due=due,
            cards_new=new,
            cards_total=total,
            reviews_today=reviews_today,
            streak_days=await self._streak_days(cockpit),
        )

    @staticmethod
    def _cockpit_scope(cockpit: str | None) -> tuple[str, str, tuple[str, ...]]:
        """Return (join clause, where clause, params) scoping counts to a cockpit."""
        if cockpit is None:
            return "", "", ()
        return (
            "JOIN decks d ON d.id = c.deck_id",
            " WHERE d.cockpit = ?",
            (cockpit,),
        )

    async def _count(self, sql: str, params: tuple[object, ...] = ()) -> int:
        cursor = await self._db.connection.execute(sql, params)
        row = await cursor.fetchone()
        return int(row["n"]) if row is not None else 0

    async def _streak_days(self, cockpit: str | None = None) -> int:
        if cockpit is None:
            cursor = await self._db.connection.execute(
                "SELECT DISTINCT substr(reviewed_at, 1, 10) AS day FROM reviews"
            )
        else:
            cursor = await self._db.connection.execute(
                "SELECT DISTINCT substr(r.reviewed_at, 1, 10) AS day FROM reviews r "
                "JOIN cards c ON c.id = r.card_id JOIN decks d ON d.id = c.deck_id "
                "WHERE d.cockpit = ?",
                (cockpit,),
            )
        days = {row["day"] for row in await cursor.fetchall()}

        today = datetime.now(UTC).date()
        if today.isoformat() not in days:
            today -= timedelta(days=1)  # a not-yet-reviewed today doesn't break the streak

        streak = 0
        while today.isoformat() in days:
            streak += 1
            today -= timedelta(days=1)
        return streak

    async def _default_deck_id(self, cockpit: str | None = None) -> int | None:
        if cockpit is None:
            cursor = await self._db.connection.execute(
                "SELECT id FROM decks ORDER BY id LIMIT 1"
            )
        else:
            cursor = await self._db.connection.execute(
                "SELECT id FROM decks WHERE cockpit = ? ORDER BY id LIMIT 1", (cockpit,)
            )
        row = await cursor.fetchone()
        return int(row["id"]) if row is not None else None

    async def _due_count(self, deck_id: int) -> int:
        now = iso_utc(utc_now())
        cursor = await self._db.connection.execute(
            "SELECT COUNT(*) AS n FROM cards WHERE deck_id = ? AND repetitions > 0 AND due_at <= ?",
            (deck_id, now),
        )
        row = await cursor.fetchone()
        return int(row["n"]) if row is not None else 0


def _card_out(row: aiosqlite.Row) -> CardOut:
    return CardOut(
        id=row["id"],
        deck_id=row["deck_id"],
        front=row["front"],
        back=row["back"],
        ipa=row["ipa"],
        register_tag=row["register_tag"],
        l1_hint=row["l1_hint"],
        examples=json.loads(row["examples"]),
        ease_factor=row["ease_factor"],
        interval_days=row["interval_days"],
        repetitions=row["repetitions"],
        due_at=row["due_at"],
    )
