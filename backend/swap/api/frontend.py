"""The built Mini App, served by the api itself, so Caddy has one upstream (ADR-0001)."""

from pathlib import Path

from fastapi import FastAPI
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from swap.api.errors import ApiError


class ImmutableStaticFiles(StaticFiles):
    """Vite's hashed build output: a file's name changes whenever its content does."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def mount_frontend(app: FastAPI, root: Path) -> None:
    """Serve `/assets/*` as immutable, root files as they are, and index.html for the rest.

    Register this after every API router, because its catch-all would shadow them.
    """
    root = root.resolve()
    index = root / "index.html"
    app.mount("/assets", ImmutableStaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            raise ApiError(404, "not_found")
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        # Every client-side route gets the shell, revalidated on each launch so a
        # deploy reaches people at once.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
