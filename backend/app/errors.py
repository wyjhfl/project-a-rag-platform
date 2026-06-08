"""Error handling for Project A RAG Platform."""
from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

def error_payload(code: str, message: str, request_id: str = "") -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get("X-Request-ID", "")


def _response(status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={"detail": message, **error_payload(code, message, request_id)},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _http_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "file_too_large",
        422: "validation_error",
        429: "rate_limited",
        503: "service_unavailable",
    }.get(status_code, "http_error")


def install_exception_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return _response(exc.status_code, exc.code, exc.message, _request_id(request))

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        message = str(exc.detail) if exc.detail else "HTTP error"
        return _response(exc.status_code, _http_error_code(exc.status_code), message, _request_id(request))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _response(422, "validation_error", str(exc), _request_id(request))
