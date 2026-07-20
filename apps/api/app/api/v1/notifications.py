"""In-app Notification Center — every route is scoped to the requesting
user's own notifications (`user_id = current_user.id`), regardless of role.
No RBAC resource: a user always manages their own notifications."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.notification_serializers import serialize_notification
from app.schemas.notifications import MarkAllReadResponse, NotificationResponse, UnreadCountResponse
from app.services.notifications.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=ApiResponse[list[NotificationResponse]])
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NotificationResponse]]:
    notifications, total = await NotificationService(db).list_for_user(
        user.organization_id, user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return ApiResponse(
        data=[serialize_notification(n) for n in notifications],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[UnreadCountResponse]:
    count = await NotificationService(db).unread_count(user.organization_id, user.id)
    return ApiResponse(data=UnreadCountResponse(count=count))


@router.post("/read-all", response_model=ApiResponse[MarkAllReadResponse])
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MarkAllReadResponse]:
    marked = await NotificationService(db).mark_all_read(user.organization_id, user.id)
    return ApiResponse(data=MarkAllReadResponse(marked_count=marked), message=f"{marked} notification(s) marked read.")


@router.patch("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NotificationResponse]:
    notification = await NotificationService(db).mark_read(notification_id, user.id)
    return ApiResponse(data=serialize_notification(notification))
