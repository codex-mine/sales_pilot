"""Request/response schemas for Communication -> Inbox & AI Reply
Classification."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationListItemResponse(BaseModel):
    id: str
    lead_id: str
    lead_full_name: str
    lead_company_name: str | None
    subject: str | None
    message_count: int
    last_message_at: datetime | None
    latest_snippet: str | None
    latest_direction: str | None
    latest_classification: str | None
    latest_confidence: float | None
    unread_count: int


class ThreadItemResponse(BaseModel):
    """A single item in the combined chronological thread — either an
    outgoing Email or an incoming Message, tagged by `direction`."""

    id: str
    direction: str  # "outbound" | "inbound"
    from_email: str
    from_name: str | None
    to_email: str | None
    subject: str | None
    body_html: str | None
    body_text: str | None
    occurred_at: datetime
    is_read: bool | None = None
    current_status: str | None = None
    reply_classification: str | None = None
    ai_suggested_action: str | None = None
    ai_confidence: float | None = None


class ConversationDetailResponse(BaseModel):
    id: str
    lead_id: str
    lead_full_name: str
    lead_company_name: str | None
    subject: str | None
    is_active: bool
    items: list[ThreadItemResponse]


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    lead_id: str
    from_email: str
    from_name: str | None
    subject: str | None
    body_text: str
    body_html: str | None
    received_at: datetime
    is_read: bool
    reply_classification: str | None
    ai_suggested_action: str | None
    ai_confidence: float | None
    ai_classified_at: datetime | None


class ReclassifyMessageRequest(BaseModel):
    classification: str = Field(min_length=1, max_length=30)


class MarkConversationReadRequest(BaseModel):
    is_read: bool = True
