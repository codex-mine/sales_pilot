"""
WebSocket endpoint streaming a single AIJob's live LangGraph step progress to
the frontend (module 13's additive streaming layer — no existing HTTP route
in `app/api/v1/ai.py` changes; `GET /ai/jobs/{id}` remains the polling
fallback `useAIJob` already uses).

Two channels are merged for the client:
- Redis pub/sub on `ai_job:{job_id}` — each `StepEvent` a graph node
  publishes (see `app/agents/base.py`), forwarded verbatim as it arrives.
- A DB poll every second — step events alone can't tell a listener when the
  AIJob row itself becomes terminal (COMPLETED/FAILED/CANCELLED), since that
  write happens *after* the graph's last node already published its
  "completed"/"failed" event (see `AIJobService.execute_job`) — so this is
  the actual terminal-state source of truth, matching what `GET /ai/jobs/{id}`
  would report.
"""

import asyncio
import contextlib
import json
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import resolve_auth_context_from_token
from app.core.config import get_settings
from app.core.redis import get_redis_pool
from app.database.session import get_db
from app.exceptions.errors import AuthenticationError, NotFoundError
from app.models.enums import AIJobStatusEnum
from app.schemas.ai_serializers import serialize_job
from app.services.ai.ai_job_service import AIJobService

router = APIRouter(tags=["ai"])

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}
_POLL_INTERVAL_SECONDS = 1.0


def _extract_ws_token(websocket: WebSocket) -> str | None:
    """Cookie first — same-site cross-port deployments (this app's
    web:3000/api:8000 split included: `SameSite` is scoped to the
    registrable domain, not the port, so the httpOnly `access_token` cookie
    already reaches the WS handshake the same way it reaches every HTTP
    request via `withCredentials`) need nothing else. The native browser
    `WebSocket` API can neither set an `Authorization` header nor read an
    httpOnly cookie into JS, so for a genuinely cross-site deployment where
    that cookie wouldn't arrive, `?token=` carries the frontend's
    already-exposed in-memory access token instead (see
    `apiClient.ts`'s `inMemoryAccessToken` — module 04 kept it specifically
    for a future Bearer-style caller; this is that caller)."""
    token = websocket.cookies.get(get_settings().access_token_cookie_name)
    if token:
        return token
    return websocket.query_params.get("token")


async def _forward_redis_messages(pubsub, websocket: WebSocket) -> None:
    async for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        await websocket.send_json({"type": "step", "event": json.loads(message["data"])})


async def _poll_until_terminal(
    websocket: WebSocket, job_id: uuid.UUID, organization_id: uuid.UUID, db: AsyncSession
) -> None:
    service = AIJobService(db)
    while True:
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        job = await service.require_job(job_id, organization_id)
        if job.status in _TERMINAL_STATUSES:
            await websocket.send_json({"type": "job_terminal", "job": serialize_job(job).model_dump(mode="json")})
            return


async def _watch_for_disconnect(websocket: WebSocket) -> None:
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


@router.websocket("/ws/ai-jobs/{job_id}")
async def stream_job_status(
    websocket: WebSocket, job_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    token = _extract_ws_token(websocket)
    if token is None:
        await websocket.close(code=4401)
        return

    try:
        auth_context = await resolve_auth_context_from_token(token, db)
    except AuthenticationError:
        await websocket.close(code=4401)
        return

    user = auth_context.user
    try:
        job = await AIJobService(db).require_job(job_id, user.organization_id)
    except NotFoundError:
        # Same "don't leak existence across tenants" behavior as the HTTP
        # route: a cross-tenant job_id closes exactly like a missing one.
        await websocket.close(code=4404)
        return

    await websocket.accept()

    redis = Redis(connection_pool=get_redis_pool())
    pubsub = redis.pubsub()
    channel = f"ai_job:{job_id}"
    try:
        await pubsub.subscribe(channel)

        # Current DB state immediately, so a client connecting mid-run isn't
        # blind to steps that already completed before it connected.
        await websocket.send_json({"type": "job_state", "job": serialize_job(job).model_dump(mode="json")})

        if job.status in _TERMINAL_STATUSES:
            return

        listen_task = asyncio.create_task(_forward_redis_messages(pubsub, websocket))
        poll_task = asyncio.create_task(_poll_until_terminal(websocket, job_id, user.organization_id, db))
        disconnect_task = asyncio.create_task(_watch_for_disconnect(websocket))
        _done, pending = await asyncio.wait(
            {listen_task, poll_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis.aclose()
        with contextlib.suppress(RuntimeError):
            await websocket.close(code=1000)
