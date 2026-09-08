"""Application factory and process-lifetime resource management.

Heavy resources (database, WebSocket registry, HTTP client, LLM client, Deepgram
client, and services) are created once and shared through ``app.state`` so the
1 GB Raspberry Pi never pays per-request setup cost.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_assist import router as assist_router
from app.api.routes_content import router as content_router
from app.api.routes_learning import router as learning_router
from app.api.routes_plan import router as plan_router
from app.api.routes_prep import router as prep_router
from app.api.routes_pt import router as pt_router
from app.api.routes_radio_ws import router as radio_ws_router
from app.api.routes_srs import router as srs_router
from app.api.websocket import router as ws_router
from app.core.budget import SpendBudget
from app.core.config import get_settings
from app.core.db import Database
from app.core.ratelimit import RateLimiter
from app.core.ws_manager import ConnectionManager
from app.services.declutter import DeclutterService
from app.services.deepgram import (
    DeepgramBudgetExceeded,
    DeepgramClient,
    DeepgramError,
    DeepgramNotConfiguredError,
    DeepgramProvider,
)
from app.services.dictionary import DictionaryService
from app.services.grammar_drill import GrammarDrillService
from app.services.llm import (
    LLMBudgetExceeded,
    LLMClient,
    LLMError,
    LLMNotConfiguredError,
    LLMProvider,
)
from app.services.monologue import MonologueService
from app.services.news import NewsService
from app.services.plan import WeeklyPlanService
from app.services.podcast import PodcastService
from app.services.prep import PrepService
from app.services.pt_generators import PtGrammarCoach, PtPracticeSentence
from app.services.pt_news import PtNewsService
from app.services.pt_seed import seed_pt_decks
from app.services.quiz import QuizService
from app.services.radio import RadioService
from app.services.register import RegisterService
from app.services.shadowing import ShadowingService
from app.services.srs import SrsService
from app.services.srs_seed import seed_default_deck
from app.services.voice import VoiceService
from app.services.whisper import (
    WhisperClient,
    WhisperError,
    WhisperNotConfiguredError,
)
from app.services.word_of_day import WordOfDayGenerator
from app.services.writing import WritingCoachService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings

    database = Database(settings.db_path)
    await database.connect()
    await database.initialize()
    await seed_default_deck(database)
    await seed_pt_decks(database)
    app.state.db = database
    app.state.srs = SrsService(database)

    ws_manager = ConnectionManager(
        heartbeat_interval=settings.ws_heartbeat_interval,
        heartbeat_timeout=settings.ws_heartbeat_timeout,
        max_connections=settings.ws_max_connections,
    )
    app.state.ws_manager = ws_manager
    heartbeat_task = asyncio.create_task(ws_manager.heartbeat_loop(), name="ws-heartbeat")

    try:
        yield
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        await ws_manager.close_all()
        await database.close()
        await app.state.http.aclose()


def create_app(
    *,
    http_client: httpx.AsyncClient | None = None,
    llm: LLMProvider | None = None,
    deepgram: DeepgramProvider | None = None,
) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            follow_redirects=True,
        )
    app.state.http = http_client

    if llm is None:
        llm = LLMClient(
            http_client,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout_seconds,
            budget=SpendBudget(settings.llm_daily_limit),
        )
    app.state.llm = llm

    if settings.stt_provider == "whisper":
        deepgram = WhisperClient(
            http_client,
            base_url=settings.whisper_base_url,
            max_retries=settings.whisper_max_retries,
            timeout=settings.whisper_timeout_seconds,
        )
    elif deepgram is None:
        deepgram = DeepgramClient(
            http_client,
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_model,
            max_retries=settings.deepgram_max_retries,
            timeout=settings.deepgram_timeout_seconds,
            budget=SpendBudget(settings.deepgram_daily_limit),
        )
    app.state.deepgram = deepgram

    app.state.news = NewsService(http_client, llm, ttl_seconds=settings.content_cache_ttl_seconds)
    app.state.podcast = PodcastService(
        http_client, llm, ttl_seconds=settings.content_cache_ttl_seconds
    )
    app.state.prep = PrepService(llm)
    app.state.declutter = DeclutterService(llm)
    app.state.voice = VoiceService(llm)
    app.state.quiz = QuizService(llm)
    app.state.register = RegisterService(llm)
    app.state.shadowing = ShadowingService(llm)
    app.state.grammar_drill = GrammarDrillService(llm)
    app.state.word_of_day = WordOfDayGenerator(llm)
    app.state.writing = WritingCoachService(llm)
    app.state.monologue = MonologueService(llm)
    app.state.plan = WeeklyPlanService(llm)
    app.state.pt_coach = PtGrammarCoach(llm)
    app.state.pt_sentence = PtPracticeSentence(llm)
    app.state.pt_news = PtNewsService(
        http_client, ttl_seconds=settings.content_cache_ttl_seconds
    )
    app.state.radio = RadioService(deepgram)
    app.state.dictionary = DictionaryService(llm, ttl_seconds=settings.dictionary_cache_ttl_seconds)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute, 60.0)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ws_router)
    app.include_router(radio_ws_router)
    app.include_router(content_router)
    app.include_router(learning_router)
    app.include_router(plan_router)
    app.include_router(srs_router)
    app.include_router(prep_router)
    app.include_router(assist_router)
    app.include_router(pt_router)

    _register_exception_handlers(app)

    settings.static_dir.mkdir(parents=True, exist_ok=True)
    settings.templates_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "llm_configured": bool(settings.llm_api_key),
            "stt_provider": settings.stt_provider,
            "deepgram_configured": bool(settings.deepgram_api_key),
            "whisper_configured": settings.stt_provider == "whisper",
        }

    @app.get("/healthz/external", tags=["system"])
    async def healthz_external() -> dict[str, str]:
        return {
            "llm": await _probe_llm(settings, http_client),
            "deepgram": await _probe_deepgram(settings, http_client),
        }

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        dist_index = settings.static_dir / "dist" / "templates" / "index.html"
        if dist_index.exists():
            return FileResponse(dist_index)
        return FileResponse(settings.templates_dir / "index.html")

    return app


async def _probe_llm(settings: Any, client: httpx.AsyncClient) -> str:
    if not settings.llm_api_key:
        return "unconfigured"
    try:
        response = await client.get(
            f"{settings.llm_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=10.0,
        )
        return "ok" if response.status_code == 200 else f"error {response.status_code}"
    except Exception:
        return "error"


async def _probe_deepgram(settings: Any, client: httpx.AsyncClient) -> str:
    if not settings.deepgram_api_key:
        return "unconfigured"
    try:
        response = await client.get(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {settings.deepgram_api_key}"},
            timeout=10.0,
        )
        return "ok" if response.status_code == 200 else f"error {response.status_code}"
    except Exception:
        return "error"


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LLMNotConfiguredError)
    async def _llm_not_configured(request: Request, exc: LLMNotConfiguredError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(LLMBudgetExceeded)
    async def _llm_budget(request: Request, exc: LLMBudgetExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(LLMError)
    async def _llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(DeepgramNotConfiguredError)
    async def _deepgram_not_configured(
        request: Request, exc: DeepgramNotConfiguredError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(DeepgramBudgetExceeded)
    async def _deepgram_budget(request: Request, exc: DeepgramBudgetExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(DeepgramError)
    async def _deepgram_error(request: Request, exc: DeepgramError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(WhisperNotConfiguredError)
    async def _whisper_not_configured(
        request: Request, exc: WhisperNotConfiguredError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(WhisperError)
    async def _whisper_error(request: Request, exc: WhisperError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


app = create_app()
