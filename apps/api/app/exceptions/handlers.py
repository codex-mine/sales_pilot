"""
Central FastAPI exception -> ApiResponse translation.

Registered once in app.main. Every error path in the API — our own AppError
subclasses, Pydantic validation failures, and anything unhandled — funnels
through here so clients only ever see one envelope shape.
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.errors import AppError
from app.schemas.common import ApiResponse

logger = structlog.get_logger(__name__)


def _error_response(
    status_code: int,
    message: str,
    *,
    errors: dict[str, list[str]] | None = None,
    meta: dict[str, object] | None = None,
) -> JSONResponse:
    body = ApiResponse(success=False, message=message, errors=errors, meta=meta)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "app_error",
            error_code=exc.error_code,
            path=request.url.path,
            status_code=exc.status_code,
        )
        errors = exc.errors or {"error_code": [exc.error_code]}
        return _error_response(exc.status_code, exc.message, errors=errors, meta=exc.meta)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"][1:]) or "body"
            field_errors.setdefault(field, []).append(error["msg"])
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed.",
            errors=field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error_response(exc.status_code, detail)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path, exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred.",
        )
