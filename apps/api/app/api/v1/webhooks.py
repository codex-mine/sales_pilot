"""
Public delivery-webhook ingestion (Email Tracking). Unauthenticated by
necessity — the sending provider, not a logged-in user, calls this — but
NEVER trusts payload content without a verified signature first (rejected
with 401 before the body is even parsed as JSON, let alone touching the DB).
"""

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.exceptions.errors import AuthenticationError, ValidationError
from app.schemas.common import ApiResponse
from app.services.communication.inbound_email_service import InboundEmailService
from app.services.email.email_tracking_service import EmailTrackingService
from app.services.email.webhook_signature import verify_inbound_webhook_auth, verify_webhook_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _parse_json_body(body: bytes) -> dict:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError("Webhook payload is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Webhook payload must be a JSON object.")
    return payload


# NOTE ON ROUTE ORDER: /email/inbound/{provider} (two segments after
# /email/) is declared before /email/{provider} (one segment) — different
# path shapes so there's no real ambiguity, but this mirrors the
# static-before-dynamic convention used everywhere else in this codebase.


@router.post("/email/inbound/{provider}", response_model=ApiResponse[None])
async def receive_inbound_email_webhook(
    provider: str, request: Request, db: AsyncSession = Depends(get_db)
) -> ApiResponse[None]:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not verify_inbound_webhook_auth(provider, body, headers):
        raise AuthenticationError("Invalid webhook authentication.")

    payload = _parse_json_body(body)
    await InboundEmailService(db).ingest_reply(provider, payload)
    return ApiResponse(message="Reply processed.")


@router.post("/email/{provider}", response_model=ApiResponse[None])
async def receive_email_webhook(
    provider: str, request: Request, db: AsyncSession = Depends(get_db)
) -> ApiResponse[None]:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not verify_webhook_signature(provider, body, headers):
        raise AuthenticationError("Invalid webhook signature.")

    payload = _parse_json_body(body)
    await EmailTrackingService(db).ingest_webhook_event(provider, payload)
    return ApiResponse(message="Event processed.")
