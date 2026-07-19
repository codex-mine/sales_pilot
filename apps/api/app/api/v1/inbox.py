"""Communication -> Inbox & AI Reply Classification routes. Reuses the
`leads` permission resource (read/update) exactly like every other
lead-adjacent module in this codebase — the Inbox is a view over Lead
conversations, not a distinct RBAC resource."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.database.session import get_db
from app.exceptions.errors import ValidationError
from app.models.enums import ReplyClassificationEnum
from app.models.identity.models import User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.common import ApiResponse
from app.schemas.inbox import (
    ConversationDetailResponse,
    ConversationListItemResponse,
    MarkConversationReadRequest,
    MessageResponse,
    ReclassifyMessageRequest,
)
from app.schemas.inbox_serializers import (
    serialize_conversation_detail,
    serialize_conversation_list_item,
    serialize_message,
)
from app.services.communication.inbound_email_service import InboundEmailService

router = APIRouter(prefix="/inbox", tags=["inbox"])

# NOTE ON ROUTE ORDER: /conversations (static) is declared before the
# /conversations/{conversation_id} family below, matching every other
# router's convention in this codebase.


@router.get("/conversations", response_model=ApiResponse[list[ConversationListItemResponse]])
async def list_conversations(
    classification: list[str] | None = Query(default=None),
    exclude_classification: list[str] | None = Query(default=None),
    unread_only: bool = Query(default=False),
    owner_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ConversationListItemResponse]]:
    # Default view excludes SPAM/OUT_OF_OFFICE unless the caller explicitly
    # asked for a classification filter that would include them.
    exclude = exclude_classification
    if not classification and exclude is None:
        exclude = [ReplyClassificationEnum.SPAM.value, ReplyClassificationEnum.OUT_OF_OFFICE.value]

    conversations, total = await ConversationRepository(db).list_inbox(
        user.organization_id,
        classifications=classification,
        exclude_classifications=exclude,
        unread_only=unread_only,
        owner_id=owner_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=[serialize_conversation_list_item(c) for c in conversations],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/conversations/{conversation_id}", response_model=ApiResponse[ConversationDetailResponse])
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ConversationDetailResponse]:
    conversation = await InboundEmailService(db).require_conversation(conversation_id, user.organization_id)
    return ApiResponse(data=serialize_conversation_detail(conversation))


@router.patch("/conversations/{conversation_id}/read", response_model=ApiResponse[ConversationDetailResponse])
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    payload: MarkConversationReadRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ConversationDetailResponse]:
    conversation = await InboundEmailService(db).mark_conversation_read(
        user.organization_id, conversation_id, is_read=payload.is_read
    )
    return ApiResponse(data=serialize_conversation_detail(conversation), message="Conversation updated.")


@router.get("/messages/{message_id}", response_model=ApiResponse[MessageResponse])
async def get_message(
    message_id: uuid.UUID,
    user: User = Depends(require_permission("leads", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MessageResponse]:
    message = await InboundEmailService(db).require_message(message_id, user.organization_id)
    return ApiResponse(data=serialize_message(message))


@router.patch("/messages/{message_id}/classification", response_model=ApiResponse[MessageResponse])
async def reclassify_message(
    message_id: uuid.UUID,
    payload: ReclassifyMessageRequest,
    user: User = Depends(require_permission("leads", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MessageResponse]:
    try:
        classification = ReplyClassificationEnum(payload.classification)
    except ValueError as exc:
        raise ValidationError(f"'{payload.classification}' is not a valid reply classification.") from exc

    message = await InboundEmailService(db).reclassify_message(
        user.organization_id, message_id, classification=classification, actor=user
    )
    return ApiResponse(data=serialize_message(message), message="Message reclassified.")
