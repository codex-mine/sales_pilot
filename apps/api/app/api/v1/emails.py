"""Email Sending routes that aren't scoped to a single Lead (Outbox, bulk
send, preview). Per-lead send/schedule/cancel live on `leads.py` as
`/leads/{lead_id}/emails/{email_id}/...` sub-resources, matching the Email
Generation module's placement — this router only holds the cross-lead views."""

import uuid

from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.models.identity.models import User
from app.repositories.email_repository import EmailRepository
from app.schemas.common import ApiResponse
from app.schemas.email_sending import (
    BulkSendRequest,
    BulkSendResponse,
    EmailPreviewResponse,
    OutboxEmailResponse,
)
from app.schemas.email_serializers import serialize_outbox_email
from app.services.email.email_sending_service import EmailSendingService

router = APIRouter(prefix="/emails", tags=["emails"])

# NOTE ON ROUTE ORDER: static-string routes (/outbox, /bulk-send) are
# declared before the `/{email_id}` family below, matching every other
# router's convention in this codebase.


@router.get("/outbox", response_model=ApiResponse[list[OutboxEmailResponse]])
async def list_outbox(
    status_filter: list[str] | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OutboxEmailResponse]]:
    emails, total = await EmailRepository(db).list_outbox(
        user.organization_id, status=status_filter, search=search, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_outbox_email(e) for e in emails],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/bulk-send", response_model=ApiResponse[BulkSendResponse])
async def bulk_send_emails(
    payload: BulkSendRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkSendResponse]:
    requested, success, errors = await EmailSendingService(db).bulk_send(
        user.organization_id, payload.lead_ids, actor=user
    )
    return ApiResponse(
        data=BulkSendResponse(
            requested_count=requested, success_count=success, failed_count=len(errors), errors=errors
        ),
        message=f"{success} of {requested} emails sent.",
    )


@router.get("/{email_id}/preview", response_model=ApiResponse[EmailPreviewResponse])
async def preview_email(
    email_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmailPreviewResponse]:
    preview = await EmailSendingService(db).preview(user.organization_id, email_id)
    return ApiResponse(data=EmailPreviewResponse(**preview))
