"""Org-level outreach sender identity settings (Settings -> Email Sender)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.email_sending import EmailSenderConnectRequest, EmailSenderStatusResponse
from app.services.email.email_sender_settings_service import EmailSenderSettingsService

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
