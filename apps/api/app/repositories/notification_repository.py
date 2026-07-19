import uuid
from typing import Any

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
