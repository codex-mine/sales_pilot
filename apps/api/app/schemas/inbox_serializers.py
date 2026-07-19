"""ORM -> response-schema mapping for the Inbox module. Combines outgoing
`Email` rows and incoming `Message` rows into one chronological thread —
the two tables stay separate (per the model's own documented reasoning),
this is purely a read-side view."""

from app.models.communication.models import Conversation, Email, Message
from app.schemas.email_serializers import _ev
from app.schemas.inbox import ConversationDetailResponse, ConversationListItemResponse, MessageResponse, ThreadItemResponse


def _snippet(text: str | None, length: int = 140) -> str | None:
    if not text:
        return None
    text = text.strip()
    return text if len(text) <= length else f"{text[:length].rstrip()}…"


def _latest_activity(conversation: Conversation) -> tuple[str, str | None, str | None, float | None] | None:
    """Returns (direction, snippet, classification, confidence) for
    whichever of the conversation's emails/messages is most recent."""
    candidates: list[tuple] = []
    for email in conversation.emails:
        occurred_at = email.sent_at or email.created_at
        candidates.append((occurred_at, "outbound", _snippet(email.body_text or email.subject), None, None))
    for message in conversation.messages:
        candidates.append(
            (message.received_at, "inbound", _snippet(message.body_text), _ev(message.reply_classification), message.ai_confidence)
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    _occurred_at, direction, snippet, classification, confidence = candidates[-1]
    return direction, snippet, classification, confidence


def serialize_conversation_list_item(conversation: Conversation) -> ConversationListItemResponse:
    lead = conversation.lead
    latest = _latest_activity(conversation)
    unread_count = sum(1 for m in conversation.messages if not m.is_read)
    return ConversationListItemResponse(
        id=str(conversation.id),
        lead_id=str(conversation.lead_id),
        lead_full_name=lead.full_name if lead else "",
        lead_company_name=lead.company_name if lead else None,
        subject=conversation.subject,
        message_count=conversation.message_count,
        last_message_at=conversation.last_message_at,
        latest_snippet=latest[1] if latest else None,
        latest_direction=latest[0] if latest else None,
        latest_classification=latest[2] if latest else None,
        latest_confidence=latest[3] if latest else None,
        unread_count=unread_count,
    )


def _email_thread_item(email: Email) -> ThreadItemResponse:
    return ThreadItemResponse(
        id=str(email.id), direction="outbound",
        from_email=email.from_email, from_name=email.from_name, to_email=email.to_email,
        subject=email.subject, body_html=email.body_html, body_text=email.body_text,
        occurred_at=email.sent_at or email.created_at,
        current_status=_ev(email.current_status),
    )


def _message_thread_item(message: Message) -> ThreadItemResponse:
    return ThreadItemResponse(
        id=str(message.id), direction="inbound",
        from_email=message.from_email, from_name=message.from_name, to_email=None,
        subject=message.subject, body_html=message.body_html, body_text=message.body_text,
        occurred_at=message.received_at, is_read=message.is_read,
        reply_classification=_ev(message.reply_classification),
        ai_suggested_action=message.ai_suggested_action, ai_confidence=message.ai_confidence,
    )


def serialize_conversation_detail(conversation: Conversation) -> ConversationDetailResponse:
    lead = conversation.lead
    items = [_email_thread_item(e) for e in conversation.emails] + [_message_thread_item(m) for m in conversation.messages]
    items.sort(key=lambda item: item.occurred_at)
    return ConversationDetailResponse(
        id=str(conversation.id),
        lead_id=str(conversation.lead_id),
        lead_full_name=lead.full_name if lead else "",
        lead_company_name=lead.company_name if lead else None,
        subject=conversation.subject,
        is_active=conversation.is_active,
        items=items,
    )


def serialize_message(message: Message) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        lead_id=str(message.lead_id),
        from_email=message.from_email,
        from_name=message.from_name,
        subject=message.subject,
        body_text=message.body_text,
        body_html=message.body_html,
        received_at=message.received_at,
        is_read=message.is_read,
        reply_classification=_ev(message.reply_classification),
        ai_suggested_action=message.ai_suggested_action,
        ai_confidence=message.ai_confidence,
        ai_classified_at=message.ai_classified_at,
    )
