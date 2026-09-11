"""Bíblia cockpit endpoints: book profiles, passage text, and exegesis studies."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import rate_limited
from app.schemas.bible import (
    BiblePrefs,
    BookProfile,
    FavoriteRequest,
    PassageText,
    StudyRecord,
    StudyRequest,
    StudySummary,
    TranslationInfo,
)
from app.services.bible_books import all_profiles
from app.services.bible_examples import BiblePassageSuggester
from app.services.bible_parser import BibleReferenceError, parse_reference
from app.services.bible_provider import (
    BibleNotConfiguredError,
    BibleTextProvider,
    BibleTranslationUnavailableError,
    BibleUpstreamError,
)
from app.services.bible_studies import BibleStudyService, LLMSchemaMismatchError
from app.services.llm import (
    LLMBudgetExceeded,
    LLMError,
    LLMJsonValidationError,
    LLMNotConfiguredError,
)

router = APIRouter(prefix="/api/bible", tags=["bible"])

logger = logging.getLogger(__name__)


@router.get("/books", response_model=list[BookProfile])
async def books() -> list[BookProfile]:
    return all_profiles()


@router.get("/example-passages", response_model=list[str])
async def example_passages(
    request: Request,
    language: str = Query(default="es"),
) -> list[str]:
    """Fresh example-passage chips for the study input.

    Never fails from the client's point of view: any LLM problem (not
    configured, budget exhausted, upstream error, malformed JSON) degrades to
    an empty list, and the frontend falls back to its curated examples.

    Deliberately NOT behind ``Depends(rate_limited)`` — same precedent as
    ``word_of_day_random`` in ``routes_content.py``. This is a cheap
    suggestion fetched on mount and on each language switch; putting it in the
    shared 30/min bucket would let a few language switches eat into the budget
    a real study submission needs.
    """
    lang = language if language in {"es", "en", "pt"} else "es"
    suggester: BiblePassageSuggester | None = getattr(
        request.app.state, "bible_examples", None
    )
    if suggester is None:  # pragma: no cover - defensive; wired in create_app
        return []
    try:
        return await suggester.suggest(lang)
    except LLMError as exc:
        # Inlined truncation: llm.py's _truncate is module-private.
        logger.warning("Bible example-passage suggestion failed: %s", str(exc)[:200])
        return []


@router.get(
    "/passage",
    response_model=PassageText,
    dependencies=[Depends(rate_limited)],
)
async def passage(
    request: Request,
    reference: str = Query(min_length=1, max_length=200),
    translation: str = Query(default="", max_length=40),
) -> PassageText:
    settings = request.app.state.settings
    label = (translation or "").strip() or settings.bible_default_translation
    try:
        ref = parse_reference(reference, translation=label)
        provider: BibleTextProvider = request.app.state.bible_provider
        text, copyright = await provider.fetch_text_with_copyright(ref, label)
    except BibleReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BibleNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BibleUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PassageText(ref=ref, passage_text=text, copyright=copyright)


@router.post(
    "/study",
    response_model=StudyRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited)],
)
async def create_study(payload: StudyRequest, request: Request) -> StudyRecord:
    settings = request.app.state.settings
    translation = (payload.translation or "").strip() or settings.bible_default_translation
    language = _resolve_language(payload.language, translation, settings)
    service: BibleStudyService = request.app.state.bible_studies
    try:
        return await service.create_study(
            payload.reference, translation=translation, language=language
        )
    except BibleReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BibleNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BibleTranslationUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except BibleUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMError as exc:
        # Re-raise the two subclasses the app already maps to their own status
        # codes, so FastAPI's registered handlers run instead of the 502 below.
        if isinstance(exc, (LLMBudgetExceeded, LLMNotConfiguredError)):
            raise
        if isinstance(exc, (LLMJsonValidationError, LLMSchemaMismatchError)):
            raise HTTPException(
                status_code=502,
                detail="El modelo no devolvió un JSON válido; vuelve a intentarlo.",
            ) from exc
        raise HTTPException(status_code=502, detail=str(exc)[:200]) from exc


@router.get("/studies", response_model=list[StudySummary])
async def list_studies(
    request: Request,
    favorites_only: bool = Query(default=False),
) -> list[StudySummary]:
    """Saved-study history; ``favorites_only`` narrows it to starred studies."""
    service: BibleStudyService = request.app.state.bible_studies
    return await service.list_studies(favorites_only=favorites_only)


@router.get("/studies/{study_id}", response_model=StudyRecord)
async def get_study(study_id: int, request: Request) -> StudyRecord:
    service: BibleStudyService = request.app.state.bible_studies
    record = await service.get_study(study_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return record


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(study_id: int, request: Request) -> None:
    service: BibleStudyService = request.app.state.bible_studies
    deleted = await service.delete_study(study_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")


@router.post("/studies/{study_id}/favorite", response_model=StudyRecord)
async def set_favorite(
    study_id: int, payload: FavoriteRequest, request: Request
) -> StudyRecord:
    """Set (or clear) the favorite flag on a saved study."""
    service: BibleStudyService = request.app.state.bible_studies
    updated = await service.set_favorite(study_id, payload.favorite)
    if not updated:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    record = await service.get_study(study_id)
    if record is None:  # pragma: no cover - defensive; it was just updated
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return record


@router.get("/translations", response_model=list[TranslationInfo])
async def translations(request: Request) -> list[TranslationInfo]:
    """Discovered translations across the spa/eng/por catalogs (for the UI)."""
    provider: BibleTextProvider = request.app.state.bible_provider
    if not provider.enabled:
        raise HTTPException(
            status_code=503,
            detail="La clave de la API de Bible no está configurada",
        )
    try:
        rows = await provider.available_translations()
    except BibleUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [TranslationInfo(**row) for row in rows]


@router.get("/prefs", response_model=BiblePrefs)
async def prefs(request: Request) -> BiblePrefs:
    """Configured translation labels for the es/en/pt UI selector."""
    settings = request.app.state.settings
    return BiblePrefs(
        es=settings.bible_default_translation,
        en=settings.bible_english_translation,
        pt=settings.bible_portuguese_translation,
    )


def _resolve_language(requested: str, translation: str, settings: Any) -> str:
    """Output language for a study: explicit request, else label mapping."""
    if requested in {"es", "en", "pt"}:
        return requested
    if translation == getattr(settings, "bible_english_translation", "NIV"):
        return "en"
    if translation == getattr(settings, "bible_portuguese_translation", "NVT"):
        return "pt"
    return "es"

