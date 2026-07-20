import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remaining_domains import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, organization_id: uuid.UUID, user_id: uuid.UUID, **fields: Any) -> Notification:
        notification = Notification(organization_id=organization_id, user_id=user_id, **fields)
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get_by_id(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        """Scoped to `user_id`, not just `organization_id` — a notification is
        owned by exactly one recipient, and this is the single gate that keeps
        a user from ever reading/mutating a teammate's notification even
        within the same org."""
        return await self.db.scalar(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )

    async def list_for_user(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, *, unread_only: bool = False,
        page: int = 1, page_size: int = 25,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.organization_id == organization_id, Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))
        base = select(Notification).where(*conditions)
        total = await self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await self.db.scalars(
            base.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result), total

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await self.db.flush()
        return notification

    async def mark_all_read(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        return result.rowcount or 0

    async def unread_count(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        ) or 0
