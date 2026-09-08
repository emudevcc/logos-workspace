"""Pericope reference parser for the Bíblia cockpit.

Accepts common PT/ES/EN book names and abbreviations plus a chapter
("Romanos 8", "Salmos 23") or a same-chapter verse range ("Rm 8:31-39").
Normalization strips accents/case so "Gênesis" and "Genesis" both resolve.
"""

from __future__ import annotations

import re
import unicodedata

from app.schemas.bible import PassageRef
from app.services.bible_books import BOOKS, Book

# Normalized alias -> matching book code(s), longest alias first.
_ALIASES: list[tuple[str, str]] = []

# When a normalized alias is ambiguous (e.g. "Jo" = João or Jó), prefer the
# first code listed here that actually matches the input.
_AMBIGUOUS_PRIORITY: dict[str, tuple[str, ...]] = {
    "jo": ("JHN", "JOB"),
}


def _norm(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )


for book in BOOKS:
    for alias in book.aliases:
        _ALIASES.append((_norm(alias), book.code))

# Longest alias first so "Cântico dos Cânticos" wins over "Cantares".
_ALIASES.sort(key=lambda item: len(item[0]), reverse=True)


class BibleReferenceError(ValueError):
    """Raised when a passage reference cannot be parsed."""


def book_by_code(code: str) -> Book | None:
    for book in BOOKS:
        if book.code == code:
            return book
    return None


def parse_reference(raw: str, translation: str = "") -> PassageRef:
    """Parse a passage string into a canonical, bounded pericope reference."""
    if not raw or not raw.strip():
        raise BibleReferenceError("Informe uma referência (ex.: Romanos 8:31-39).")

    normalized = _norm(raw.strip())
    matched: list[tuple[int, str, str]] = []  # (alias length, code, remainder)
    seen: set[tuple[str, str]] = set()
    for alias, code in _ALIASES:
        if not normalized.startswith(alias):
            continue
        remainder = normalized[len(alias) :]
        if remainder and not remainder[0].isspace() and remainder[0] not in ".:":
            continue
        key = (alias, code)
        if key in seen:
            continue
        seen.add(key)
        matched.append((len(alias), code, remainder.strip()))

    if not matched:
        raise BibleReferenceError(
            f"Não reconheci o livro em '{raw.strip()}'. "
            "Use um nome ou abreviatura conhecida (ex.: Rm, Gênesis, 1Co)."
        )

    # Prefer the longest alias; resolve equal-length ambiguity via priority.
    longest = max(item[0] for item in matched)
    candidates = [item for item in matched if item[0] == longest]
    chosen = candidates[0]
    if len(candidates) > 1:
        codes = [item[1] for item in candidates]
        priority = _AMBIGUOUS_PRIORITY.get(normalized[:longest], ())
        for code in priority:
            if code in codes:
                chosen = next(item for item in candidates if item[1] == code)
                break

    book = book_by_code(chosen[1])
    if book is None:
        raise BibleReferenceError("Livro não encontrado no cânon de 66 livros.")

    position = chosen[2]
    match = re.fullmatch(r"(\d{1,3})(?::(\d{1,3})(?:-(\d{1,3}))?)?", position)
    if match is None:
        raise BibleReferenceError(
            f"Não entendi a passagem '{raw.strip()}'. Use o formato "
            "'Livro capítulo:versículo' (ex.: Romanos 8:31-39) ou capítulo inteiro."
        )

    chapter = int(match.group(1))
    start_verse = int(match.group(2)) if match.group(2) else None
    end_verse = int(match.group(3)) if match.group(3) else None
    if chapter < 1:
        raise BibleReferenceError("Capítulo inválido.")
    if start_verse is not None and start_verse < 1:
        raise BibleReferenceError("Versículo inicial inválido.")
    if start_verse is not None and end_verse is not None and end_verse < start_verse:
        raise BibleReferenceError("O versículo final é menor que o inicial.")

    display = f"{book.name_pt} {chapter}"
    if start_verse is not None:
        display += f":{start_verse}"
        if end_verse is not None and end_verse != start_verse:
            display += f"-{end_verse}"

    return PassageRef(
        book_code=book.code,
        book_name_pt=book.name_pt,
        chapter=chapter,
        start_verse=start_verse,
        end_verse=end_verse,
        display=display,
        translation=translation or "",
    )
