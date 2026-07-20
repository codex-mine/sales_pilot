"""Request/response schemas for Campaigns -> Multi-Step Sequence Automation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CampaignLeadStatusEnum, CampaignStatusEnum, SequenceStepTypeEnum

CAMPAIGN_STATUS_CHOICES: list[str] = [s.value for s in CampaignStatusEnum]
CAMPAIGN_LEAD_STATUS_CHOICES: list[str] = [s.value for s in CampaignLeadStatusEnum]
# V1 scope: linkedin_message / linkedin_connection / webhook exist on the enum
# for future extensibility but are rejected here with a clear "not yet
# supported" error rather than silently accepted and doing nothing.
SUPPORTED_STEP_TYPES: list[str] = [
    SequenceStepTypeEnum.EMAIL.value, SequenceStepTypeEnum.WAIT.value, SequenceStepTypeEnum.TASK.value,
]
_DEFAULT_SEND_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def _validate_step_type(value: str) -> str:
    if value not in SUPPORTED_STEP_TYPES:
        raise ValueError(
            f"Step type '{value}' is not yet supported. Supported types: {', '.join(SUPPORTED_STEP_TYPES)}."
        )
    return value


# ─── Campaign ────────────────────────────────────────────────────────────────────


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    goal: str | None = Field(default=None, max_length=512)
    target_industry: str | None = Field(default=None, max_length=100)
    target_company_size: str | None = Field(default=None, max_length=50)
    target_job_titles: list[str] | None = None
    value_proposition: str | None = None
    daily_send_limit: int = Field(default=50, ge=1, le=2000)
    timezone: str = Field(default="UTC", max_length=50)
    send_days: list[str] = Field(default_factory=lambda: list(_DEFAULT_SEND_DAYS))
    send_start_hour: int = Field(default=9, ge=0, le=23)
    send_end_hour: int = Field(default=17, ge=0, le=23)
    owner_id: uuid.UUID | None = None
    requires_approval: bool = Field(
        default=True,
        description="Full-automation gate. True (default, safe): sequence email steps are left as "
        "DRAFT and await manual approval before sending. False: the scheduler generates and sends "
        "without human review.",
    )

    @field_validator("send_end_hour")
    @classmethod
    def _validate_window(cls, value: int, info) -> int:
        start = info.data.get("send_start_hour")
        if start is not None and value <= start:
            raise ValueError("send_end_hour must be after send_start_hour.")
        return value


class CampaignUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    goal: str | None = Field(default=None, max_length=512)
    target_industry: str | None = Field(default=None, max_length=100)
    target_company_size: str | None = Field(default=None, max_length=50)
    target_job_titles: list[str] | None = None
    value_proposition: str | None = None
    daily_send_limit: int | None = Field(default=None, ge=1, le=2000)
    timezone: str | None = Field(default=None, max_length=50)
    send_days: list[str] | None = None
    send_start_hour: int | None = Field(default=None, ge=0, le=23)
    send_end_hour: int | None = Field(default=None, ge=0, le=23)
    owner_id: uuid.UUID | None = None
    requires_approval: bool | None = None


class CampaignOwnerResponse(BaseModel):
    id: str
    full_name: str
    email: str


class CampaignFunnelCounts(BaseModel):
    enrolled: int
    in_progress: int
    replied: int
    meeting_booked: int
    completed: int
    opted_out: int
    bounced: int


class CampaignResponse(BaseModel):
    id: str
    organization_id: str
    owner: CampaignOwnerResponse | None
    name: str
    description: str | None
    status: str
    goal: str | None
    target_industry: str | None
    target_company_size: str | None
    target_job_titles: list[str] | None
    value_proposition: str | None
    daily_send_limit: int
    timezone: str
    send_days: list[str]
    send_start_hour: int
    send_end_hour: int
    requires_approval: bool
    started_at: datetime | None
    completed_at: datetime | None
    enrolled_count: int
    funnel: CampaignFunnelCounts | None = None
    created_at: datetime
    updated_at: datetime


# ─── Sequence ────────────────────────────────────────────────────────────────────


class SequenceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class SequenceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class SequenceStepCreateRequest(BaseModel):
    step_type: str
    step_order: int = Field(ge=1)
    delay_days: int = Field(default=0, ge=0, le=365)
    delay_hours: int = Field(default=0, ge=0, le=23)
    email_template_id: uuid.UUID | None = None
    content_source: str = Field(
        default="template",
        description="'template' (uses email_template_id) or 'ai_personalized' (generates per lead).",
    )
    subject_override: str | None = Field(default=None, max_length=512)
    body_override: str | None = None
    condition: dict | None = Field(
        default=None, description='e.g. {"skip_if": "opened"} or {"skip_if": "replied"}'
    )
    is_active: bool = True

    _validate_step_type = field_validator("step_type")(_validate_step_type)

    @field_validator("content_source")
    @classmethod
    def _validate_content_source(cls, value: str) -> str:
        if value not in ("template", "ai_personalized"):
            raise ValueError("content_source must be 'template' or 'ai_personalized'.")
        return value


class SequenceStepUpdateRequest(BaseModel):
    step_order: int | None = Field(default=None, ge=1)
    delay_days: int | None = Field(default=None, ge=0, le=365)
    delay_hours: int | None = Field(default=None, ge=0, le=23)
    email_template_id: uuid.UUID | None = None
    content_source: str | None = None
    subject_override: str | None = Field(default=None, max_length=512)
    body_override: str | None = None
    condition: dict | None = None
    is_active: bool | None = None

    @field_validator("content_source")
    @classmethod
    def _validate_content_source(cls, value: str | None) -> str | None:
        if value is not None and value not in ("template", "ai_personalized"):
            raise ValueError("content_source must be 'template' or 'ai_personalized'.")
        return value


class SequenceStepTemplateSummary(BaseModel):
    id: str
    name: str
    subject: str
    total_sent: int
    total_opened: int
    total_replied: int
    open_rate: float
    reply_rate: float


class SequenceStepResponse(BaseModel):
    id: str
    sequence_id: str
    step_type: str
    step_order: int
    delay_days: int
    delay_hours: int
    email_template_id: str | None
    email_template: SequenceStepTemplateSummary | None
    content_source: str
    subject_override: str | None
    body_override: str | None
    condition: dict | None
    is_active: bool


class SequenceResponse(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str | None
    is_active: bool
    steps: list[SequenceStepResponse]
    created_at: datetime


# ─── Enrollment ──────────────────────────────────────────────────────────────────


class EnrollLeadRequest(BaseModel):
    lead_id: uuid.UUID
    sequence_id: uuid.UUID | None = None


class BulkEnrollRequest(BaseModel):
    lead_ids: list[uuid.UUID] = Field(min_length=1)
    sequence_id: uuid.UUID | None = None


class EnrollByFilterRequest(BaseModel):
    """Mirrors `GET /leads`'s query filters exactly (same field names) — the
    service translates these into the same `LeadRepository.list_for_organization`
    keyword arguments the Leads list route already uses, never reimplementing
    lead filtering."""

    sequence_id: uuid.UUID | None = None
    search: str | None = Field(default=None, max_length=255)
    status: list[str] | None = None
    source: list[str] | None = None
    owner_id: list[uuid.UUID] | None = None
    tag: list[str] | None = None
    country: str | None = None
    industry: str | None = None
    company: str | None = None
    favorite: bool | None = None
    archived: bool | None = None
    lead_score_min: float | None = None
    lead_score_max: float | None = None
    priority_min: int | None = None
    priority_max: int | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None


class BulkEnrollResponse(BaseModel):
    requested_count: int
    enrolled_count: int
    skipped_count: int
    errors: list[str]


class CampaignLeadLeadSummary(BaseModel):
    id: str
    full_name: str
    email: str | None
    company_name: str | None
    status: str


class CampaignLeadResponse(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str | None = None
    lead: CampaignLeadLeadSummary | None
    sequence_id: str | None
    status: str
    current_step_order: int
    next_step_id: str | None
    next_step_type: str | None
    next_action_at: datetime | None
    enrolled_at: datetime
    completed_at: datetime | None
    opted_out_at: datetime | None


# ─── Dashboard ───────────────────────────────────────────────────────────────────


class CampaignDashboardResponse(BaseModel):
    campaign_id: str
    status: str
    funnel: CampaignFunnelCounts
    total_enrolled: int
    emails_sent: int
    open_rate: float
    reply_rate: float
    meeting_rate: float
