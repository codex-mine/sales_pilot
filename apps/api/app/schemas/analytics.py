"""Request/response schemas for Analytics -> Dashboard, Reports & Notification Center."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

REPORT_TYPE_CHOICES: list[str] = ["pipeline", "campaign_performance", "ai_usage", "email_performance"]
# V1 scope: no croniter/cron-expression dependency — `schedule_cron` stores one
# of these three cadence presets rather than real cron syntax, despite the
# column name inherited from the `Report` model.
SCHEDULE_CADENCE_CHOICES: list[str] = ["daily", "weekly", "monthly"]
DATE_RANGE_PRESETS: list[str] = ["today", "last_7_days", "last_30_days", "this_month", "last_month", "all_time"]


# ─── Dashboard summary ───────────────────────────────────────────────────────────


class PipelineFunnelResponse(BaseModel):
    counts: dict[str, int]


class AIUsageJobTypeBreakdown(BaseModel):
    job_type: str
    job_count: int
    total_tokens: int
    cost_usd: float


class AIDailyCostPoint(BaseModel):
    date: str
    cost_usd: float


class AIUsageAnalyticsResponse(BaseModel):
    total_cost_usd: float
    total_job_count: int
    total_tokens: int
    by_job_type: list[AIUsageJobTypeBreakdown]
    daily_cost_trend: list[AIDailyCostPoint]


class CampaignPerformanceItem(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    enrolled_count: int
    replied_count: int
    meeting_booked_count: int
    reply_rate: float


class CampaignPerformanceResponse(BaseModel):
    campaigns: list[CampaignPerformanceItem]


class EmailPerformanceSummary(BaseModel):
    open_rate: float
    click_rate: float
    bounce_rate: float


class UpcomingMeetingItem(BaseModel):
    id: str
    title: str
    lead_full_name: str | None
    scheduled_start: datetime | None


class MeetingsSummary(BaseModel):
    by_status: dict[str, int]
    booked_this_month: int
    upcoming: list[UpcomingMeetingItem]


class RecentActivityItem(BaseModel):
    id: str
    activity_type: str
    summary: str | None
    actor_name: str | None
    occurred_at: datetime


class DashboardSummaryResponse(BaseModel):
    pipeline_funnel: PipelineFunnelResponse
    ai_usage: AIUsageAnalyticsResponse
    campaign_performance: CampaignPerformanceResponse
    email_performance: EmailPerformanceSummary
    meetings: MeetingsSummary
    recent_activity: list[RecentActivityItem]
    unread_notification_count: int


# ─── Dashboard widgets ───────────────────────────────────────────────────────────


class DashboardWidgetResponse(BaseModel):
    id: str
    widget_type: str
    title: str
    position_x: int
    position_y: int
    width: int
    height: int
    config: dict | None


class CreateDashboardWidgetRequest(BaseModel):
    widget_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    width: int = Field(default=4, ge=1, le=12)
    height: int = Field(default=3, ge=1, le=12)
    config: dict | None = None


class UpdateDashboardWidgetRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    position_x: int | None = Field(default=None, ge=0)
    position_y: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1, le=12)
    height: int | None = Field(default=None, ge=1, le=12)
    config: dict | None = None


# ─── Reports ─────────────────────────────────────────────────────────────────────


class ReportConfigSchema(BaseModel):
    """Validated shape of `Report.config` (JSONB) — checked at creation time
    so a malformed filter/column set fails clearly with a 422 instead of
    breaking later when the report is run."""

    filters: dict[str, Any] = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list)
    date_range: str = Field(default="last_30_days")
    group_by: str | None = None

    @field_validator("date_range")
    @classmethod
    def _validate_date_range(cls, value: str) -> str:
        if value not in DATE_RANGE_PRESETS:
            raise ValueError(f"date_range must be one of: {', '.join(DATE_RANGE_PRESETS)}.")
        return value


class CreateReportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    report_type: str
    config: ReportConfigSchema = Field(default_factory=ReportConfigSchema)
    is_scheduled: bool = False
    schedule_cron: str | None = None
    recipients: list[EmailStr] | None = None

    @field_validator("report_type")
    @classmethod
    def _validate_report_type(cls, value: str) -> str:
        if value not in REPORT_TYPE_CHOICES:
            raise ValueError(f"report_type must be one of: {', '.join(REPORT_TYPE_CHOICES)}.")
        return value

    @field_validator("schedule_cron")
    @classmethod
    def _validate_schedule_cron(cls, value: str | None) -> str | None:
        if value is not None and value not in SCHEDULE_CADENCE_CHOICES:
            raise ValueError(f"schedule_cron must be one of: {', '.join(SCHEDULE_CADENCE_CHOICES)}.")
        return value


class UpdateReportRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    config: ReportConfigSchema | None = None
    is_scheduled: bool | None = None
    schedule_cron: str | None = None
    recipients: list[EmailStr] | None = None

    @field_validator("schedule_cron")
    @classmethod
    def _validate_schedule_cron(cls, value: str | None) -> str | None:
        if value is not None and value not in SCHEDULE_CADENCE_CHOICES:
            raise ValueError(f"schedule_cron must be one of: {', '.join(SCHEDULE_CADENCE_CHOICES)}.")
        return value


class ReportResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    report_type: str
    config: ReportConfigSchema | None
    is_scheduled: bool
    schedule_cron: str | None
    recipients: list[str] | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunReportResponse(BaseModel):
    report: ReportResponse
    row_count: int
    delivered_to: list[str]
