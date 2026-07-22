import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.agents.base import bootstrap_checkpoint_tables
from app.api.v1.router import router
from app.api.v1.ws_ai_jobs import router as ws_ai_jobs_router
from app.core.asyncio_compat import ensure_selector_event_loop_policy
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import engine
from app.exceptions.handlers import register_exception_handlers

# Must run before any event loop is created (see module docstring) — the
# AI LangGraph engine's Postgres checkpointer needs a selector-based loop
# on Windows, so this has to land before uvicorn/pytest-asyncio spins one up.
ensure_selector_event_loop_policy()

settings = get_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Must run once, at true cold start, before this process ever opens a
    # transaction that could conflict with it — see `bootstrap_checkpoint_tables`'s
    # docstring for why this can't happen lazily inside a job execution.
    await bootstrap_checkpoint_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    lifespan=_lifespan,
)

# Serves uploaded organization logos (see app/services/storage_service.py).
# Not under api_v1_prefix — media is static content, not a versioned API.
_uploads_dir = Path(settings.upload_dir)
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_uploads_dir)), name="media")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_and_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


register_exception_handlers(app)
app.include_router(router, prefix=settings.api_v1_prefix)
# WebSocket routes: FastAPI mounts them via include_router the same way as
# HTTP routes, but the CORSMiddleware/@app.middleware("http") above are
# HTTP-only and never run for a WS handshake — ws_ai_jobs.py does its own
# auth (see `_extract_ws_token`) since there's no middleware chain to lean on.
app.include_router(ws_ai_jobs_router, prefix=settings.api_v1_prefix)
