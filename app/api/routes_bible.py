"""Bíblia cockpit endpoints: book profiles, passage text, and exegesis studies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import rate_limited
from app.schemas.bible import (
    BiblePrefs,
    BookProfile,
    PassageText,
    StudyRecord,
    StudyRequest,
    StudySummary,
    TranslationInfo,
)
from app.services.bible_books import all_profiles
from app.services.bible_parser import BibleReferenceError, parse_reference
from app.services.bible_provider import (
    BibleNotConfiguredError,
    BibleTextProvider,
    BibleTranslationUnavailableError,
    BibleUpstreamError,
)
from app.services.bible_studies import BibleStudyService

router = APIRouter(prefix="/api/bible", tags=["bible"])


@router.get("/books", response_model=list[BookProfile])
async def books() -> list[BookProfile]:
    return all_profiles()


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
        text = await provider.fetch_text(ref, label)
    except BibleReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BibleNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BibleUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PassageText(ref=ref, passage_text=text)


@router.post(
    "/study",
    response_model=StudyRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited)],
)
async def create_study(payload: StudyRequest, request: Request) -> StudyRecord:
    settings = request.app.state.settings
    translation = (payload.translation or "").strip() or settings.bible_default_translation
    service: BibleStudyService = request.app.state.bible_studies
    try:
        return await service.create_study(payload.reference, translation=translation)
    except BibleReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BibleNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BibleTranslationUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except BibleUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/studies", response_model=list[StudySummary])
async def list_studies(request: Request) -> list[StudySummary]:
    service: BibleStudyService = request.app.state.bible_studies
    return await service.list_studies()


@router.get("/studies/{study_id}", response_model=StudyRecord)
async def get_study(study_id: int, request: Request) -> StudyRecord:
    service: BibleStudyService = request.app.state.bible_studies
    record = await service.get_study(study_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Estudo não encontrado")
    return record


@router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(study_id: int, request: Request) -> None:
    service: BibleStudyService = request.app.state.bible_studies
    deleted = await service.delete_study(study_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Estudo não encontrado")


@router.get("/translations", response_model=list[TranslationInfo])
async def translations(request: Request) -> list[TranslationInfo]:
    """Discovered translations across the spa/eng/por catalogs (for the UI)."""
    provider: BibleTextProvider = request.app.state.bible_provider
    if not provider.enabled:
        raise HTTPException(status_code=503, detail="Bible API key is not configured")
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

