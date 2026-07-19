"""Request/response schemas for Communication -> Email Sending Infrastructure.
Send/schedule/cancel reuse `EmailResponse` (app.schemas.email_generation) —
same Email row, no parallel response shape."""

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleEmailRequest(BaseModel):
    scheduled_at: datetime


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


class UnsubscribeInfoResponse(BaseModel):
    lead_first_name: str | None
    organization_name: str
    already_unsubscribed: bool


class UnsubscribeConfirmResponse(BaseModel):
    lead_first_name: str | None
    organization_name: str
