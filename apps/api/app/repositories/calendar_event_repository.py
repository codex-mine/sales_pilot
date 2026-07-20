import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication.models import CalendarEvent


class CalendarEventRepository:
    """Create/update only — reads go through `Meeting.calendar_event`
    (eager-loaded by `MeetingRepository`), never a standalone lookup, since a
    CalendarEvent is only ever meaningful in the context of its Meeting."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, organization_id: uuid.UUID, **fields: Any) -> CalendarEvent:
        event = CalendarEvent(organization_id=organization_id, **fields)
        self.db.add(event)
        await self.db.flush()
        return event

    async def update(self, event: CalendarEvent, changes: dict[str, Any]) -> CalendarEvent:
        for field, value in changes.items():
            setattr(event, field, value)
        await self.db.flush()
        return event
