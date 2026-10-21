"""The api: FastAPI for the Mini App, plus the built frontend when `STATIC_DIR` is set.

Run it with `uvicorn swap.api.app:create_app --factory`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute

from swap import __version__
from swap.api import health
from swap.api.errors import install_problem_handlers
from swap.api.frontend import mount_frontend
from swap.api.headers import SecurityHeadersMiddleware
from swap.config import Settings, get_settings
from swap.db import Sessionmaker, create_engine, create_sessionmaker
from swap.logs import configure_logging


def _operation_id(route: APIRoute) -> str:
    # The handler's own name ("get_me"), which is what the generated client shows.
    return route.name


def create_app(
    settings: Settings | None = None, *, sessionmaker: Sessionmaker | None = None
) -> FastAPI:
    """Build the app. Tests pass a `sessionmaker` bound to their own transaction."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format, settings.secrets())

    engine = None
    if sessionmaker is None:
        engine = create_engine(settings.database_url)
        sessionmaker = create_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            await engine.dispose()

    app = FastAPI(
        title="Swap",
        version=__version__,
        lifespan=lifespan,
        # The docs UIs load scripts from a CDN, which the CSP forbids. The schema itself
        # is public anyway: the repository is.
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        generate_unique_id_function=_operation_id,
    )
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker
    app.add_middleware(SecurityHeadersMiddleware)
    install_problem_handlers(app)
    app.include_router(health.router)
    if settings.static_dir:
        mount_frontend(app, Path(settings.static_dir))
    return app
