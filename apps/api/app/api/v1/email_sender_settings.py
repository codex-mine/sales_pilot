"""Org-level outreach sender identity settings (Settings -> Email Sender /
Sender Mailbox Management)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.email_sending import (
    CreateSenderMailboxRequest,
    EmailSenderConnectRequest,
    EmailSenderStatusResponse,
    SenderMailboxResponse,
    TestSmtpConnectionRequest,
    UpdateSenderMailboxRequest,
)
from app.schemas.email_serializers import serialize_sender_mailbox
from app.services.email.email_sender_settings_service import EmailSenderSettingsService
from app.services.email.sender_client import test_smtp_connection

router = APIRouter(prefix="/settings/email-sender", tags=["settings"])


@router.get("", response_model=ApiResponse[EmailSenderStatusResponse])
async def get_email_sender_settings(
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailSenderStatusResponse]:
    status_data = await EmailSenderSettingsService(db).status(user.organization_id)
    return ApiResponse(data=EmailSenderStatusResponse(**status_data))


@router.post("", response_model=ApiResponse[EmailSenderStatusResponse])
async def connect_email_sender(
    payload: EmailSenderConnectRequest,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailSenderStatusResponse]:
    service = EmailSenderSettingsService(db)
    await service.connect(
        organization_id=user.organization_id, host=payload.host, port=payload.port,
        username=payload.username, password=payload.password, use_tls=payload.use_tls,
        daily_send_limit=payload.daily_send_limit, actor=user,
    )
    status_data = await service.status(user.organization_id)
    return ApiResponse(data=EmailSenderStatusResponse(**status_data), message="Sending mailbox connected.")


@router.delete("/{integration_id}", response_model=ApiResponse[None])
async def disconnect_email_sender(
    integration_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await EmailSenderSettingsService(db).disconnect(
        organization_id=user.organization_id, integration_id=integration_id, actor=user
    )
    return ApiResponse(message="Sending mailbox disconnected.")


# ─── Sender Mailbox Management (multi-mailbox) ────────────────────────────────────
# Static-string paths declared before `/mailboxes/{mailbox_id}` so a literal
# segment like "test-connection" never gets swallowed by the `{mailbox_id}`
# path param — same convention as every other router in this codebase.


@router.post("/mailboxes/test-connection", response_model=ApiResponse[None])
async def test_sender_mailbox_connection(
    payload: TestSmtpConnectionRequest,
    user: User = Depends(require_permission("campaigns", "manage")),
) -> ApiResponse[None]:
    await test_smtp_connection(
        host=payload.host, port=payload.port, username=payload.username, password=payload.password,
        encryption_type=payload.encryption_type,
    )
    return ApiResponse(message="Connection succeeded.")


@router.get("/mailboxes", response_model=ApiResponse[list[SenderMailboxResponse]])
async def list_sender_mailboxes(
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SenderMailboxResponse]]:
    mailboxes = await EmailSenderSettingsService(db).list_mailboxes(user.organization_id)
    return ApiResponse(data=[serialize_sender_mailbox(m) for m in mailboxes])


@router.post("/mailboxes", response_model=ApiResponse[SenderMailboxResponse], status_code=201)
async def create_sender_mailbox(
    payload: CreateSenderMailboxRequest,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SenderMailboxResponse]:
    mailbox = await EmailSenderSettingsService(db).create_mailbox(user.organization_id, payload=payload, actor=user)
    return ApiResponse(data=serialize_sender_mailbox(mailbox), message="Sender mailbox connected.")


@router.patch("/mailboxes/{mailbox_id}", response_model=ApiResponse[SenderMailboxResponse])
async def update_sender_mailbox(
    mailbox_id: uuid.UUID,
    payload: UpdateSenderMailboxRequest,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SenderMailboxResponse]:
    service = EmailSenderSettingsService(db)
    mailbox = await service.require_mailbox(user.organization_id, mailbox_id)
    mailbox = await service.update_mailbox(mailbox, payload=payload, actor=user)
    return ApiResponse(data=serialize_sender_mailbox(mailbox), message="Sender mailbox updated.")


@router.delete("/mailboxes/{mailbox_id}", response_model=ApiResponse[None])
async def delete_sender_mailbox(
    mailbox_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await EmailSenderSettingsService(db).delete_mailbox(user.organization_id, mailbox_id, actor=user)
    return ApiResponse(message="Sender mailbox deleted.")


@router.post("/mailboxes/{mailbox_id}/set-default", response_model=ApiResponse[SenderMailboxResponse])
async def set_default_sender_mailbox(
    mailbox_id: uuid.UUID,
    user: User = Depends(require_permission("campaigns", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SenderMailboxResponse]:
    mailbox = await EmailSenderSettingsService(db).set_default_mailbox(user.organization_id, mailbox_id, actor=user)
    return ApiResponse(data=serialize_sender_mailbox(mailbox), message="Default mailbox updated.")
