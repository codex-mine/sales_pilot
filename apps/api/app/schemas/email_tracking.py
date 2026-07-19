"""Request/response schemas for Communication -> Email Open/Click Tracking &
Delivery Events."""

from datetime import datetime

from pydantic import BaseModel


class EmailEventResponse(BaseModel):
    id: str
    email_id: str
    event_type: str
    occurred_at: datetime
    provider: str | None
    ip_address: str | None
    user_agent: str | None
    click_url: str | None
    bounce_reason: str | None
    metadata: dict | None


class EmailTimelineResponse(BaseModel):
    email_id: str
    current_status: str
    events: list[EmailEventResponse]


class EmailPerformanceDailyPoint(BaseModel):
    date: str
    sent: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    open_rate: float
    click_rate: float
    bounce_rate: float


class EmailPerformanceAnalyticsResponse(BaseModel):
    window_days: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_complained: int
    open_rate: float
    click_rate: float
    bounce_rate: float
    daily: list[EmailPerformanceDailyPoint]
