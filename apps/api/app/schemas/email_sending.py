"""Request/response schemas for Communication -> Email Sending Infrastructure.
Send/schedule/cancel reuse `EmailResponse` (app.schemas.email_generation) —
same Email row, no parallel response shape."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class ScheduleEmailRequest(BaseModel):
    scheduled_at: datetime


class ComposeEmailRequest(BaseModel):
    """Phase X Issue 08 — Send Custom Email from Lead Detail. `to_email`
    defaults to the lead's own email when omitted; `send_now=False` saves a
    DRAFT that can be sent/scheduled later through the existing
    `/leads/{lead_id}/emails/{email_id}/send` (or `/schedule`) routes, same
    as an AI-generated draft."""

    to_email: EmailStr | None = None
    to_name: str | None = Field(default=None, max_length=255)
    subject: str = Field(min_length=1, max_length=512)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    reply_to: EmailStr | None = None
    sender_mailbox_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    send_now: bool = True


class BulkSendRequest(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=200)


class BulkSendResponse(BaseModel):
    requested_count: int
    success_count: int
    failed_count: int
    errors: list[str]


class EmailPreviewResponse(BaseModel):
    subject: str
    body_html: str
    body_text: str | None
    to_email: str
    to_name: str | None
    from_email: str
    from_name: str | None


class OutboxEmailResponse(BaseModel):
    id: str
    lead_id: str
    lead_full_name: str | None
    lead_company_name: str | None
    from_email: str
    from_name: str | None
    to_email: str
    to_name: str | None
    subject: str
    current_status: str
    ai_generated: bool
    send_error: str | None
    send_retry_count: int
    bounce_reason: str | None = None
    scheduled_at: datetime | None
    sent_at: datetime | None
    created_at: datetime


class EmailSenderConnectRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=1, max_length=512)
    use_tls: bool = True
    daily_send_limit: int | None = Field(default=None, ge=1, le=10_000)


class EmailSenderStatusResponse(BaseModel):
    is_connected: bool
    integration_id: str | None
    host: str | None
    port: int | None
    username: str | None
    use_tls: bool | None
    has_platform_fallback: bool
    daily_send_limit: int
    sent_today: int


# ─── Sender Mailbox Management (multi-mailbox) ────────────────────────────────────

ENCRYPTION_TYPE_CHOICES: list[str] = ["none", "starttls", "ssl"]


def _validate_encryption_type(value: str | None) -> str | None:
    if value is not None and value not in ENCRYPTION_TYPE_CHOICES:
        raise ValueError(f"encryption_type must be one of: {', '.join(ENCRYPTION_TYPE_CHOICES)}.")
    return value


class TestSmtpConnectionRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=1, max_length=512)
    encryption_type: str = Field(default="starttls")

    _validate_encryption_type = field_validator("encryption_type")(_validate_encryption_type)


class CreateSenderMailboxRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email_address: str = Field(min_length=1, max_length=255)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=1, max_length=512)
    encryption_type: str = Field(default="starttls")
    from_name: str | None = Field(default=None, max_length=255)
    reply_to: str | None = Field(default=None, max_length=255)
    is_default: bool = False
    daily_send_limit: int | None = Field(default=None, ge=1, le=10_000)

    _validate_encryption_type = field_validator("encryption_type")(_validate_encryption_type)


class UpdateSenderMailboxRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email_address: str | None = Field(default=None, min_length=1, max_length=255)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=1, max_length=512)
    encryption_type: str | None = None
    from_name: str | None = Field(default=None, max_length=255)
    reply_to: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    daily_send_limit: int | None = Field(default=None, ge=1, le=10_000)

    _validate_encryption_type = field_validator("encryption_type")(_validate_encryption_type)


class SenderMailboxResponse(BaseModel):
    id: str
    name: str
    email_address: str | None
    host: str
    port: int
    username: str | None
    encryption_type: str
    from_name: str | None
    reply_to: str | None
    is_default: bool
    is_active: bool
    daily_send_limit: int | None
    created_at: datetime
    updated_at: datetime


class UnsubscribeInfoResponse(BaseModel):
    lead_first_name: str | None
    organization_name: str
    already_unsubscribed: bool


class UnsubscribeConfirmResponse(BaseModel):
    lead_first_name: str | None
    organization_name: str
