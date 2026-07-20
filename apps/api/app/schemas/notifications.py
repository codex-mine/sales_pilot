"""Request/response schemas for the in-app Notification Center."""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: str | None
    action_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked_count: int
