"""RFC 9457 problem responses, each with a machine `code` that the UI translates.

`title` is for developers. People only ever see the dictionary string the UI
looks up by `code` (ADR-0007, ADR-0009).
"""

from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from swap.errors import DomainError

PROBLEM_JSON = "application/problem+json"


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str | None = None


class ApiError(Exception):
    """Raise anywhere in a request to answer with a problem response.

    Domain code raises `DomainError` instead, which is answered the same way.
    """

    def __init__(self, status: int, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.detail = detail


def problem_response(
    status: int,
    code: str,
    detail: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = Problem(title=HTTPStatus(status).phrase, status=status, code=code, detail=detail)
    return JSONResponse(
        body.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def on_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return problem_response(exc.status, exc.code, exc.detail)

    @app.exception_handler(DomainError)
    async def on_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return problem_response(exc.status, exc.code, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 404 → "not_found", 405 → "method_not_allowed", and so on.
        code = HTTPStatus(exc.status_code).name.lower()
        return problem_response(exc.status_code, code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Locations and messages only. FastAPI's default echoes the input back, and the
        # input can be someone's initData.
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return problem_response(422, "validation_error", detail)
