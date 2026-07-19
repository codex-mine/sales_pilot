"""
Communication Domain — Email, EmailEvent, Conversation, Message, Meeting, CalendarEvent.

Architecture decisions:
- Email events are STRICTLY append-only (EmailEvent table).
  We never update Email.status directly after send — we derive the current status
  from the most recent EmailEvent. This gives us:
  1. Complete delivery timeline per email
  2. Accurate time-to-open, time-to-click metrics
  3. Webhook idempotency (re-delivered events are just duplicate rows, easily filtered)

- Conversation groups emails between our system and a lead into a thread.
  A Conversation contains Messages (our outgoing emails + their replies).
  This models a realistic email thread without fighting IMAP threading.

- Meeting is distinct from CalendarEvent.
  Meeting = our internal record of what we're trying to schedule.
  CalendarEvent = the external calendar system's record (Google/Outlook).
  A Meeting may have 0 or 1 linked CalendarEvent.

- Reply is a sub-record of Message for AI-classified incoming messages.
  It stores the AI classification (interested, not_interested, etc.)
  and the suggested next action separately from the raw message content.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    EmailEventTypeEnum, EmailStatusEnum,
    MeetingStatusEnum, ReplyClassificationEnum,
)

if TYPE_CHECKING:
    from app.models.identity.models import User, Organization
    from app.models.crm.models import Lead
    from app.models.campaigns.models import CampaignLead, SequenceStep


class Email(BaseModel):
    """
    A single outgoing email sent to a lead.

    An Email belongs to a Lead (always), optionally to a CampaignLead and SequenceStep
    (if sent as part of an automated sequence), or to a Conversation (if part of a thread).

    current_status is a derived/cached field, updated by the EmailEvent processor.
    The authoritative state is the last EmailEvent row. The cached status exists for
    fast list queries without a subquery on EmailEvent every time.
    """
    __tablename__ = "emails"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    campaign_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_leads.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    sequence_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequence_steps.id", ondelete="SET NULL"),
        nullable=True
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    sent_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Set when this Email was created from (or saved as) an EmailTemplate — "
        "drives EmailTemplate.total_sent/total_opened/total_replied analytics."
    )

    # Content
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tracking
    current_status: Mapped[EmailStatusEnum] = mapped_column(
        String(20), default=EmailStatusEnum.DRAFT, nullable=False, index=True
    )
    external_message_id: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, unique=True,
        comment="Message-ID header from the email provider (for threading)"
    )
    tracking_pixel_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True,
        comment="Unique ID embedded in tracking pixel URL"
    )
    is_open_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    is_click_tracked: Mapped[bool] = mapped_column(Boolean, default=True)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Send failure tracking (Email Sending module). Additive columns: the
    # outbox view needs to show *why* a send failed (suppressed recipient vs.
    # a transient provider error) and how many attempts were made, mirroring
    # AIJob.error_message/retry_count for the identical reason — without
    # these, a FAILED row's reason is lost the moment the Celery task exits.
    send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    send_retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # AI info
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    personalization_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Variables used during template rendering (for debugging/re-gen)"
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="emails")
    campaign_lead: Mapped[Optional["CampaignLead"]] = relationship(
        "CampaignLead", back_populates="emails"
    )
    sequence_step: Mapped[Optional["SequenceStep"]] = relationship(
        "SequenceStep", back_populates="emails"
    )
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation", back_populates="emails"
    )
    events: Mapped[List["EmailEvent"]] = relationship(
        "EmailEvent", back_populates="email",
        cascade="all, delete-orphan",
        order_by="EmailEvent.occurred_at"
    )

    __table_args__ = (
        Index("ix_emails_org_status", "organization_id", "current_status"),
        Index("ix_emails_org_lead", "organization_id", "lead_id"),
        Index("ix_emails_sent_at", "sent_at"),
        Index("ix_emails_tracking_pixel", "tracking_pixel_id"),
    )


class EmailEvent(BaseModel):
    """
    Append-only email event log.

    Each delivery/engagement event creates a new row. This is the canonical
    source of truth for email status. We never update rows here.

    provider_event_id: The ID from the email provider's webhook payload.
    Used for idempotency — duplicate webhook deliveries won't create duplicate events
    (unique constraint on provider_event_id).

    metadata stores provider-specific data: bounce reason, click URL, geo info, etc.
    """
    __tablename__ = "email_events"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    event_type: Mapped[EmailEventTypeEnum] = mapped_column(
        String(30), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Email provider: sendgrid, ses, mailgun, postmark"
    )
    provider_event_id: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
        comment="Provider's unique event ID for idempotency"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    click_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bounce_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    email: Mapped["Email"] = relationship("Email", back_populates="events")

    __table_args__ = (
        UniqueConstraint("provider_event_id", name="uq_email_event_provider_id"),
        Index("ix_email_events_email_type", "email_id", "event_type"),
        Index("ix_email_events_occurred", "occurred_at"),
        Index("ix_email_events_org_type", "organization_id", "event_type"),
    )


class Conversation(BaseModel):
    """
    An email thread between our system and a lead.
    Groups all outgoing emails and incoming replies into a single thread.
    """
    __tablename__ = "conversations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead")
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="conversation")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.received_at"
    )

    __table_args__ = (
        Index("ix_conversations_org_lead", "organization_id", "lead_id"),
        Index("ix_conversations_last_message", "last_message_at"),
    )


class Message(BaseModel):
    """
    A single message within a Conversation. This represents INCOMING messages
    (replies from the prospect). Outgoing messages are Email records.

    Why separate Message from Email?
    Incoming emails come from the prospect's email client with different fields
    (raw headers, threading references) and go through AI classification.
    Mixing them with outgoing Email records would complicate the schema.
    """
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    in_reply_to_email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="SET NULL"), nullable=True,
        comment="The Email this message is a reply to"
    )
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI classification (populated after AI reply analysis agent runs)
    reply_classification: Mapped[Optional[ReplyClassificationEnum]] = mapped_column(
        String(30), nullable=True, index=True
    )
    ai_suggested_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_classified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation", "conversation_id"),
        Index("ix_messages_classification", "reply_classification"),
        Index("ix_messages_received_at", "received_at"),
    )


class Meeting(BaseModel):
    """
    A meeting request or scheduled meeting with a lead.

    A Meeting is created when:
    1. AI detects a meeting request in a reply (auto)
    2. User manually creates one from the UI

    calendar_event_id links to the external calendar system record.
    """
    __tablename__ = "meetings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    calendar_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_events.id", ondelete="SET NULL"),
        nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[MeetingStatusEnum] = mapped_column(
        String(20), default=MeetingStatusEnum.PROPOSED, nullable=False, index=True
    )
    proposed_times: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="List of proposed datetime slots offered to the prospect"
    )
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    meeting_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="meetings")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    calendar_event: Mapped[Optional["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="meeting"
    )

    __table_args__ = (
        Index("ix_meetings_org_status", "organization_id", "status"),
        Index("ix_meetings_scheduled_start", "scheduled_start"),
    )


class CalendarEvent(BaseModel):
    """
    External calendar system event (Google Calendar / Outlook).
    Stores the provider's event ID for sync and update operations.
    """
    __tablename__ = "calendar_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True,
        comment="Which calendar integration created this event"
    )
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="google_calendar | outlook_calendar"
    )
    provider_event_id: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="External event ID from the calendar provider"
    )
    provider_calendar_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    meet_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attendees: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    meeting: Mapped[Optional["Meeting"]] = relationship(
        "Meeting", back_populates="calendar_event", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_calendar_event_provider"),
        Index("ix_calendar_events_start", "start_time"),
    )
