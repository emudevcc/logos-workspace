"""De-clutter, voice roleplay, radio, and speech-connector endpoints."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import rate_limited
from app.schemas.assist import (
    CorrectRequest,
    CorrectResult,
    DeclutterRequest,
    DeclutterResult,
    MonologueEvaluateRequest,
    MonologueFeedback,
    QuizItem,
    QuizRequest,
    RadioStation,
    RegisterRequest,
    RegisterResult,
    TranscribeRequest,
    Transcript,
    VoiceTurnRequest,
    VoiceTurnResponse,
)
from app.services.connectors import DISCOURSE_CONNECTORS
from app.services.declutter import DeclutterService
from app.services.monologue import MonologueService
from app.services.quiz import QuizService
from app.services.radio import RadioService
from app.services.register import RegisterService
from app.services.voice import VoiceService
from app.services.writing import WritingCoachService

router = APIRouter(prefix="/api", tags=["assist"])


@router.post(
    "/declutter",
    response_model=DeclutterResult,
    dependencies=[Depends(rate_limited)],
)
async def declutter(payload: DeclutterRequest, request: Request) -> DeclutterResult:
    service: DeclutterService = request.app.state.declutter
    return await service.declutter(payload)


@router.post(
    "/writing/correct",
    response_model=CorrectResult,
    dependencies=[Depends(rate_limited)],
)
async def writing_correct(payload: CorrectRequest, request: Request) -> CorrectResult:
    service: WritingCoachService = request.app.state.writing
    return await service.correct(payload.draft)


@router.post(
    "/voice/turn",
    response_model=VoiceTurnResponse,
    dependencies=[Depends(rate_limited)],
)
async def voice_turn(payload: VoiceTurnRequest, request: Request) -> VoiceTurnResponse:
    service: VoiceService = request.app.state.voice
    return await service.turn(payload)


@router.get("/radio/stations", response_model=list[RadioStation])
async def radio_stations(request: Request) -> list[RadioStation]:
    service: RadioService = request.app.state.radio
    return service.stations()


@router.post(
    "/radio/transcribe",
    response_model=Transcript,
    dependencies=[Depends(rate_limited)],
)
async def radio_transcribe(payload: TranscribeRequest, request: Request) -> Transcript:
    allowed_hosts: list[str] = request.app.state.settings.deepgram_allowed_hosts
    if allowed_hosts:
        host = urlparse(payload.audio_url).hostname
        if host not in allowed_hosts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="audio_url host is not allowed",
            )
    service: RadioService = request.app.state.radio
    return await service.transcribe(payload.audio_url)


@router.get("/speech/connectors", response_model=list[str])
async def speech_connectors() -> list[str]:
    return list(DISCOURSE_CONNECTORS)


@router.get("/speech/topics", response_model=list[str])
async def speech_topics(request: Request) -> list[str]:
    service: MonologueService = request.app.state.monologue
    return service.topics()


@router.post(
    "/speech/monologue/evaluate",
    response_model=MonologueFeedback,
    dependencies=[Depends(rate_limited)],
)
async def monologue_evaluate(
    payload: MonologueEvaluateRequest,
    request: Request,
) -> MonologueFeedback:
    service: MonologueService = request.app.state.monologue
    return await service.evaluate(payload.topic, payload.transcript, payload.duration_seconds)


@router.post(
    "/quiz",
    response_model=QuizItem,
    dependencies=[Depends(rate_limited)],
)
async def quiz(payload: QuizRequest, request: Request) -> QuizItem:
    service: QuizService = request.app.state.quiz
    return await service.generate(payload.text)


@router.post(
    "/register/rewrite",
    response_model=RegisterResult,
    dependencies=[Depends(rate_limited)],
)
async def register_rewrite(payload: RegisterRequest, request: Request) -> RegisterResult:
    service: RegisterService = request.app.state.register
    return await service.rewrite(payload.text, payload.register_tag)
