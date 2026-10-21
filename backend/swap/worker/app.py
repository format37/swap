"""The worker process: APScheduler, plus the relay's endpoint for the bot.

    uvicorn swap.worker.app:create_app --factory --host 127.0.0.1 --port 8707

On the VPS it runs in the host's network, because the Bot API server listens on the
host's loopback only (ADR-0008). Without TELEGRAM_API_BASE it runs no bot at all.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from swap.bot.handlers import build_router
from swap.bot.relay import relay_authorized, to_update
from swap.bot.setup import configure_bot, make_bot
from swap.config import Settings, get_settings
from swap.db import Sessionmaker, create_engine, create_sessionmaker
from swap.logs import configure_logging
from swap.worker.jobs import beat

log = structlog.get_logger("swap.worker")

HEARTBEAT_EVERY_S = 30


def create_app(
    settings: Settings | None = None,
    *,
    sessionmaker: Sessionmaker | None = None,
    bot: Bot | None = None,
) -> Starlette:
    """Build the worker. Tests pass their own `sessionmaker` and a recording `bot`."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format, settings.secrets())

    engine = None
    if sessionmaker is None:
        engine = create_engine(settings.database_url)
        sessionmaker = create_sessionmaker(engine)
    if bot is None and settings.telegram_api_base:
        bot = make_bot(settings, settings.telegram_api_base)

    dispatcher: Dispatcher | None = None
    if bot is not None:
        dispatcher = Dispatcher(sessionmaker=sessionmaker, settings=settings)
        dispatcher.include_router(build_router())

    scheduler = AsyncIOScheduler(timezone=UTC)
    scheduler.add_job(
        beat,
        "interval",
        seconds=HEARTBEAT_EVERY_S,
        args=[sessionmaker],
        id="heartbeat",
        next_run_time=datetime.now(UTC),
        coalesce=True,
        max_instances=1,
    )
    # Updates being handled in the background; kept so none is garbage-collected
    # mid-flight, and so shutdown can wait for them.
    pending: set[asyncio.Task[object]] = set()

    def finished(task: asyncio.Task[object]) -> None:
        pending.discard(task)
        if not task.cancelled() and (error := task.exception()) is not None:
            log.error("update failed", exc_info=error)

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "telegram": bot is not None})

    async def relay(request: Request) -> JSONResponse:
        if bot is None or dispatcher is None:
            return JSONResponse({"code": "telegram_disabled"}, status_code=503)
        if not relay_authorized(request.headers.get("authorization"), bot.token):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse({"code": "malformed"}, status_code=400)
        update = to_update(payload, bot)
        if update is not None:
            # Answer the relay at once, as gptaidbot does: its thread waits for this
            # response, and the bot's reply goes out through the Bot API anyway.
            task: asyncio.Task[object] = asyncio.create_task(dispatcher.feed_update(bot, update))
            pending.add(task)
            task.add_done_callback(finished)
        # Anything but "empty" makes the relay try to send a reply of its own.
        return JSONResponse({"type": "empty"})

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        scheduler.start()
        if bot is not None:
            try:
                await configure_bot(bot, settings.webapp_url)
            except Exception:
                # A Bot API server that is down must not stop the sweeps.
                log.exception("bot profile setup failed")
        log.info("worker started", telegram=bot is not None)
        yield
        scheduler.shutdown(wait=False)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if bot is not None:
            await bot.session.close()
        if engine is not None:
            await engine.dispose()

    app = Starlette(
        routes=[Route("/healthz", healthz), Route("/message", relay, methods=["POST"])],
        lifespan=lifespan,
    )
    app.state.pending = pending
    return app
