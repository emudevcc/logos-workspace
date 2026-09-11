"""Bíblia study service: pericope exegesis generation and persistence.

Generates the six-section study report (user spec §2) through the LLM with
deterministic book-profile grounding and guardrail instructions (spec §3).
The output language follows the caller's choice (es/en/pt; Spanish default),
matching the passage-translation language selected in the UI. Reports are
persisted so studies can be re-opened from history.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from app.core.db import Database
from app.core.timeutil import iso_utc, utc_now
from app.schemas.bible import BibleStudy, StudyRecord, StudySummary
from app.services.bible_books import BOOKS, Book
from app.services.bible_parser import book_by_code, parse_reference
from app.services.bible_provider import BibleTextProvider
from app.services.llm import LLMError, LLMJsonValidationError, LLMProvider

logger = logging.getLogger(__name__)

VALID_LANGUAGES: tuple[str, str, str] = ("es", "en", "pt")

_JSON_SHAPE = (
    '{"text_literary": {"genre": "...", "authorial_tone": "...", '
    '"unit_division": "..."}, "historical_grammatical": {"author": "...", '
    '"recipients": "...", "date": "...", "geopolitical_context": "...", '
    '"occasion": "..."}, "lexical_exegesis": [{"term": "...", '
    '"transliteration": "...", "lemma": "...", "parsing": "...", '
    '"contextual_definition": "...", "consensus_note": "..."}], '
    '"redemptive_theological": {"placement_redemptive_history": "...", '
    '"cross_references": ["..."], "christological_significance": "..."}, '
    '"core_principle": "...", "practical_application": {"action_items": ["..."], '
    '"reflection_prompts": ["..."], "obedience_areas": ["..."]}, '
    '"guardrail_notes": "..."}'
)

# System prompts localized per output language (guardrails of the agreed spec).
_SYSTEM_BY_LANG = {
    "es": (
        "Eres un exégeta bíblico evangélico y conservador que produce estudios de "
        "pasajes según el método histórico-gramatical. Trabajas en español.\n\n"
        "GUARDARRAILS OBLIGATORIOS:\n"
        "1. Prioridad literal-gramatical: el sentido primario reside en la "
        "intención del autor en su contexto histórico-gramatical; rechaza la "
        "alegorización especulativa.\n"
        "2. Ortodoxia evangélica histórica: sola Scriptura, justificación por la "
        "fe, alta visión de la inspiración e inerrancia bíblica.\n"
        "3. Nada de teologizar sin cita: toda afirmación sobre griego/hebreo y "
        "trasfondo histórico debe apoyarse en el consenso léxico e histórico "
        "documentado; explica la base en 'consensus_note' de cada término.\n\n"
        "Usa SOLO los datos del perfil del libro provistos (autor, fecha, ocasión); "
        "si algo no consta, escríbelo como incierto. Responde SOLAMENTE con JSON "
        "con esta forma exacta:\n" + _JSON_SHAPE
    ),
    "en": (
        "You are a conservative evangelical biblical exegete producing passage "
        "studies using the historical-grammatical method. Work in English.\n\n"
        "MANDATORY GUARDRAILS:\n"
        "1. Literal-grammatical priority: the primary meaning lies in the author's "
        "intent within its original historical-grammatical context; reject "
        "speculative allegorization.\n"
        "2. Historic evangelical orthodoxy: sola Scriptura, justification by "
        "faith, a high view of Scripture's inspiration and inerrancy.\n"
        "3. No uncited theologizing: every claim about Greek/Hebrew and "
        "historical background must rest on documented lexical and historical "
        "consensus; explain the basis in each term's 'consensus_note'.\n\n"
        "Use ONLY the book-profile facts provided (author, date, occasion); if "
        "something is not stated, mark it as uncertain. Respond ONLY with JSON in "
        "exactly this shape:\n" + _JSON_SHAPE
    ),
    "pt": (
        "Você é um exegeta bíblico evangélico e conservador que produz estudos de "
        "passagens segundo o método histórico-gramatical. Trabalhe em português.\n\n"
        "GUARDAS OBRIGATÓRIAS:\n"
        "1. Prioridade literal-gramatical: o sentido primário reside na intenção "
        "do autor no seu contexto histórico-gramatical; rejeite a alegorização "
        "especulativa.\n"
        "2. Ortodoxia evangélica histórica: sola Scriptura, justificação pela fé, "
        "alta visão da inspiração e inerrância bíblica.\n"
        "3. Nada de teologizar sem citação: toda afirmação sobre grego/hebraico e "
        "contexto histórico deve apoiar-se em consenso lexical e histórico "
        "documentado; explique a base no 'consensus_note' de cada termo.\n\n"
        "Use SOMENTE os dados do perfil do livro fornecidos (autor, data, ocasião); "
        "se algo não constar, escreva como incerto. Responda SOMENTE com JSON com "
        "esta forma exata:\n" + _JSON_SHAPE
    ),
}

_JSON_RETRY_HINT = {
    "es": (
        "\n\nIMPORTANTE: Devuelve ÚNICAMENTE un objeto JSON válido con exactamente "
        "la forma indicada; sin bloques de código ni texto adicional."
    ),
    "en": (
        "\n\nIMPORTANT: Return ONLY a single valid JSON object in exactly the shape "
        "above; no markdown fences and no extra text."
    ),
    "pt": (
        "\n\nIMPORTANTE: Responda APENAS com um objeto JSON válido na forma exata "
        "indicada; sem blocos de código nem texto extra."
    ),
}

# A schema mismatch is a different failure from malformed JSON: the JSON parsed
# fine but its fields don't match the required shape, so a "return valid JSON"
# reminder cannot fix it. These hints name the offending field paths instead.
_SCHEMA_RETRY_HINT = {
    "es": (
        "\n\nCORRECCIÓN OBLIGATORIA: tu respuesta anterior tenía JSON válido pero no "
        "respetaba el esquema indicado. Errores de validación: {fields}. Devuelve de "
        "nuevo el objeto completo corrigiendo exactamente esos campos (respeta la "
        "forma y los límites indicados, p. ej. 2-3 elementos en 'lexical_exegesis')."
    ),
    "en": (
        "\n\nMANDATORY CORRECTION: your previous response was valid JSON but did not "
        "match the required schema. Validation errors: {fields}. Return the full "
        "object again, fixing exactly those fields (respect the documented shape and "
        "limits, e.g. 2-3 items in 'lexical_exegesis')."
    ),
    "pt": (
        "\n\nCORREÇÃO OBRIGATÓRIA: a tua resposta anterior tinha JSON válido mas não "
        "respeitava o esquema indicado. Erros de validação: {fields}. Devolve de novo "
        "o objeto completo corrigindo exatamente esses campos (respeita a forma e os "
        "limites indicados, p. ex. 2-3 elementos em 'lexical_exegesis')."
    ),
}


class LLMSchemaMismatchError(LLMError):
    """Raised when a parsed LLM response fails ``BibleStudy`` validation.

    Holds Pydantic's ``(loc, msg)`` pairs so the retry hint can name the failing
    field paths. Never carries ``input`` — the model's own output values stay
    out of prompts, logs, and client-facing messages.
    """

    def __init__(self, message: str, errors: list[ErrorDetails]) -> None:
        super().__init__(message)
        self.errors = errors


def _format_errors(errors: list[ErrorDetails]) -> str:
    """Render Pydantic errors as ``"."-joined field path: message`` pairs."""
    rendered: list[str] = []
    for error in errors:
        loc = ".".join(str(part) for part in error.get("loc", ())) or "(root)"
        rendered.append(f"{loc}: {error.get('msg', 'invalid')}")
    return "; ".join(rendered) or "unknown"


def _schema_retry_hint(errors: list[ErrorDetails], language: str) -> str:
    """Localized corrective hint naming the fields that failed validation."""
    return _SCHEMA_RETRY_HINT[language].format(fields=_format_errors(errors))


_USER_BY_LANG = {
    "es": (
        "Perfil del libro (datos deterministas):\n{profile}\n\n"
        "Pasaje estudiado: {reference} ({translation})\n\n"
        "Texto del pasaje:\n{passage_text}\n\n"
        "La sección 2 debe usar los datos del perfil y marcar como incierto lo que "
        "no conste. En la sección 3 analiza 2-3 palabras originales clave del pasaje "
        "(griego en el NT, hebreo/arameo en el AT). La sección 4 ubica el pasaje en "
        "la historia redentora, da referencias cruzadas breves y su sentido "
        "cristológico legítimo. La sección 6 ofrece aplicaciones concretas y "
        "prácticas."
    ),
    "en": (
        "Book profile (deterministic data):\n{profile}\n\n"
        "Passage studied: {reference} ({translation})\n\n"
        "Passage text:\n{passage_text}\n\n"
        "Section 2 must use the profile data and mark as uncertain anything not "
        "stated there. In section 3 analyze 2-3 pivotal original-language words of "
        "the passage (Greek in the NT, Hebrew/Aramaic in the OT). Section 4 places "
        "the passage in redemptive history, gives brief cross-references, and its "
        "legitimate christological sense. Section 6 offers concrete, practical "
        "applications."
    ),
    "pt": (
        "Perfil do livro (dados determinísticos):\n{profile}\n\n"
        "Passagem estudada: {reference} ({translation})\n\n"
        "Texto da passagem:\n{passage_text}\n\n"
        "A seção 2 deve usar os dados do perfil e marcar como incerto o que não "
        "constar. Na seção 3 analise 2-3 palavras originais-chave da passagem "
        "(grego no NT, hebraico/aramaico no AT). A seção 4 situa a passagem na "
        "história da redenção, dá referências cruzadas breves e o seu sentido "
        "cristológico legítimo. A seção 6 oferece aplicações concretas e práticas."
    ),
}


class BibleStudyService:
    def __init__(
        self,
        db: Database,
        llm: LLMProvider,
        provider: BibleTextProvider,
        max_report_tokens: int = 2400,
    ) -> None:
        self._db = db
        self._llm = llm
        self._provider = provider
        self._max_report_tokens = max_report_tokens

    async def create_study(
        self, reference: str, translation: str = "", language: str = ""
    ) -> StudyRecord:
        """Parse a reference, fetch the passage, generate and persist a study."""
        ref = parse_reference(reference, translation=translation)
        label = ref.translation
        passage_text = await self._provider.fetch_text(ref, label)
        report = await self._build_report(ref, passage_text, label, language)

        now = iso_utc(utc_now())
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                "INSERT INTO studies "
                "(reference, translation, book_code, chapter, start_verse, end_verse, "
                " passage_text, report, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ref.display,
                    label,
                    ref.book_code,
                    ref.chapter,
                    ref.start_verse,
                    ref.end_verse,
                    passage_text,
                    report.model_dump_json(),
                    now,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Falha ao criar o estudo (sem id retornado)")
            study_id = int(cursor.lastrowid)

        return StudyRecord(
            id=study_id,
            reference=ref.display,
            translation=label,
            book_code=ref.book_code,
            created_at=now,
            passage_text=passage_text,
            report=report,
        )

    async def _build_report(
        self, ref: Any, passage_text: str, translation: str, language: str = ""
    ) -> BibleStudy:
        language = language if language in VALID_LANGUAGES else "es"
        profile = book_by_code(ref.book_code)
        if profile is None:
            raise LLMError(f"Perfil do livro ausente para {ref.book_code}")
        profile_text = _profile_for_prompt(profile)
        system = _SYSTEM_BY_LANG[language]
        user = _USER_BY_LANG[language].format(
            profile=profile_text,
            reference=ref.display,
            translation=translation,
            passage_text=passage_text,
        )
        raw: dict[str, Any] | None = None
        report: BibleStudy | None = None
        last_error: LLMError | None = None
        for attempt in range(2):
            hint = "" if last_error is None else _hint_for(last_error, language)
            try:
                raw = await self._llm.complete_json(
                    system=system + hint,
                    user=user,
                    max_tokens=self._max_report_tokens,
                    temperature=0.2 if attempt == 0 else 0.1,
                )
            except LLMJsonValidationError as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning(
                        "bible study retry reason=%s ref=%s", type(exc).__name__, ref.display
                    )
                    continue
                logger.error(
                    "bible study failed reason=%s ref=%s", type(exc).__name__, ref.display
                )
                raise
            try:
                report = BibleStudy.model_validate(raw)
                break
            except ValidationError as exc:
                # Only loc/msg — never `include_input=True`, which would echo
                # the model's own field values back into the next prompt.
                last_error = LLMSchemaMismatchError(
                    "Estudio bíblico: respuesta fuera del esquema "
                    f"({_format_errors(exc.errors())})",
                    exc.errors(),
                )
                if attempt == 0:
                    logger.warning(
                        "bible study retry reason=%s ref=%s fields=%s",
                        type(last_error).__name__,
                        ref.display,
                        _format_errors(exc.errors()),
                    )
                    continue
                logger.error(
                    "bible study failed reason=%s ref=%s fields=%s",
                    type(last_error).__name__,
                    ref.display,
                    _format_errors(exc.errors()),
                )
                raise last_error from exc
        if report is None:  # pragma: no cover - defensive; loop breaks or raises
            raise last_error or LLMError("Estudio bíblico: falha sem erro registrado")
        # Echo the authoritative reference and text — never the model's version.
        return report.model_copy(
            update={
                "reference": ref.display,
                "translation": translation,
                "passage_text": passage_text,
            }
        )

    async def list_studies(self) -> list[StudySummary]:
        cursor = await self._db.connection.execute(
            "SELECT id, reference, translation, book_code, created_at "
            "FROM studies ORDER BY id DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
        return [
            StudySummary(
                id=int(row["id"]),
                reference=str(row["reference"]),
                translation=str(row["translation"]),
                book_code=str(row["book_code"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    async def get_study(self, study_id: int) -> StudyRecord | None:
        cursor = await self._db.connection.execute(
            "SELECT * FROM studies WHERE id = ?", (study_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        report = BibleStudy.model_validate(json.loads(row["report"]))
        return StudyRecord(
            id=int(row["id"]),
            reference=str(row["reference"]),
            translation=str(row["translation"]),
            book_code=str(row["book_code"]),
            created_at=str(row["created_at"]),
            passage_text=str(row["passage_text"]),
            report=report,
        )

    async def delete_study(self, study_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM studies WHERE id = ?", (study_id,))
            return cursor.rowcount > 0


def _hint_for(last_error: LLMError, language: str) -> str:
    """Corrective hint appended to the system prompt on the retry attempt.

    Returns an empty string for any other ``LLMError`` subtype — those never
    reach a retry, and a wrong-type guess must not raise deep in the loop.
    """
    if isinstance(last_error, LLMJsonValidationError):
        return _JSON_RETRY_HINT[language]
    if isinstance(last_error, LLMSchemaMismatchError):
        return _schema_retry_hint(last_error.errors, language)
    return ""


def _profile_for_prompt(book: Book) -> str:
    return (
        f"- Livro: {book.name_pt} (código {book.code}, {book.testament})\n"
        f"- Gênero literário: {book.genre}\n"
        f"- Autor (consenso): {book.author}\n"
        f"- Data aproximada: {book.date}\n"
        f"- Ocasião/propósito: {book.occasion}"
    )


def all_books() -> tuple[Book, ...]:
    return BOOKS
