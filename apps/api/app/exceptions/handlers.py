from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR


def register_exception_handlers(app: FastAPI) -> None:
    """Keep every API error in the public response envelope."""
    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors: dict[str, list[str]] = {}
        for error in exc.errors():
            location = ".".join(str(item) for item in error["loc"])
            errors.setdefault(location, []).append(error["msg"])
        return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_ENTITY, content={"success": False, "data": None, "message": "Validation failed", "errors": errors, "meta": None})
    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content={"success": False, "data": None, "message": "Internal server error", "errors": None, "meta": None})
