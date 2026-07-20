"""
Notification Center -> read/management only. Creation happens in the modules
that already write `Notification` rows (09 inbox, 10 meetings, 11 campaigns) —
this service deliberately has no generic "create notification" method, so
nothing lets an arbitrary caller spam a user's notification feed.

Every method is scoped to `(organization_id, user_id)`, and the read/mutate
methods additionally re-derive `user_id` from an already-loaded `Notification`
row rather than trusting a caller-supplied id, so a user can never touch a
teammate's notification even within the same organization.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.remaining_domains import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    async def list_for_user(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, *, unread_only: bool = False,
        page: int = 1, page_size: int = 25,
    ) -> tuple[list[Notification], int]:
        return await self.notifications.list_for_user(
            organization_id, user_id, unread_only=unread_only, page=page, page_size=page_size
        )

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = await self.notifications.get_by_id(notification_id, user_id)
        if notification is None:
            raise NotFoundError("Notification not found.")
        if notification.is_read:
            return notification
        notification = await self.notifications.mark_read(notification)
        await self.db.commit()
        return notification

    async def mark_all_read(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> int:
        marked = await self.notifications.mark_all_read(organization_id, user_id)
        await self.db.commit()
        return marked

    async def unread_count(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return await self.notifications.unread_count(organization_id, user_id)
