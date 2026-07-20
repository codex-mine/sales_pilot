"""ORM -> response-schema mapping for the Notification Center."""

from app.models.remaining_domains import Notification
from app.schemas.notifications import NotificationResponse


def serialize_notification(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        notification_type=notification.notification_type,
        title=notification.title,
        body=notification.body,
        entity_type=notification.entity_type,
        entity_id=str(notification.entity_id) if notification.entity_id else None,
        action_url=notification.action_url,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )
