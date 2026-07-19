"""Request/response schemas for the Lead Management module (CRM -> Leads)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import LeadStatusEnum

# The set of lead statuses this module's UI curates out of the full, broader
# LeadStatusEnum. Kept here, not as a DB constraint, so it stays purely
# additive/display-layer. RESEARCHING / RESEARCH_DONE / EMAIL_GENERATED /
# UNSUBSCRIBED / OPENED / BOUNCED were reserved above for the AI Research,
# Email Generation, Email Sending, and Email Tracking modules — each sets
# its status via the same validated LeadService.update() path, so they're
# included here now that all four exist. REPLIED/UNQUALIFIED remain reserved
# for module 09 (Reply Handling) until something writes them.
LEAD_STATUS_CHOICES: list[str] = [
    LeadStatusEnum.NEW.value,
    LeadStatusEnum.RESEARCHING.value,
    LeadStatusEnum.RESEARCH_DONE.value,
    LeadStatusEnum.EMAIL_GENERATED.value,
    LeadStatusEnum.CONTACTED.value,
    LeadStatusEnum.OPENED.value,
    LeadStatusEnum.QUALIFIED.value,
    LeadStatusEnum.INTERESTED.value,
    LeadStatusEnum.DEMO_SCHEDULED.value,
    LeadStatusEnum.PROPOSAL.value,
    LeadStatusEnum.NEGOTIATION.value,
    LeadStatusEnum.WON.value,
    LeadStatusEnum.LOST.value,
    LeadStatusEnum.BOUNCED.value,
    LeadStatusEnum.UNSUBSCRIBED.value,
]

LEAD_SOURCE_CHOICES: list[str] = [
    "website", "manual", "csv_import", "referral", "linkedin", "apollo",
    "google_maps", "facebook", "cold_email", "advertisement", "api", "custom",
]

_COMPANY_SIZES = {"1", "2-10", "11-50", "51-200", "201-1000", "1001-5000", "5000+"}


class LeadAddress(BaseModel):
    line1: str | None = Field(default=None, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)


def _validate_company_size(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in _COMPANY_SIZES:
        raise ValueError(f"Company size must be one of: {', '.join(sorted(_COMPANY_SIZES))}.")
    return value


# ─── Requests ──────────────────────────────────────────────────────────────────

class LeadCreateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default="manual", max_length=100)
    status: str = Field(default=LeadStatusEnum.NEW.value)
    priority: int = Field(default=0, ge=0, le=100)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address: LeadAddress | None = None
    linkedin_url: str | None = Field(default=None, max_length=512)
    twitter_url: str | None = Field(default=None, max_length=512)
    company_size: str | None = None
    revenue: float | None = Field(default=None, ge=0)
    employee_count: int | None = Field(default=None, ge=0)
    owner_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=5000)
    lead_score: float | None = Field(default=None, ge=0, le=100)

    _validate_company_size = field_validator("company_size")(_validate_company_size)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        if value not in LEAD_STATUS_CHOICES:
            raise ValueError(f"Status must be one of: {', '.join(LEAD_STATUS_CHOICES)}.")
        return value


class LeadUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics. Also covers the single-lead
    favorite/archive toggle (`is_favorite`/`is_archived`) rather than adding
    dedicated routes for them; bulk favorite/archive has its own action on
    `POST /leads/bulk`."""
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    status: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address: LeadAddress | None = None
    linkedin_url: str | None = Field(default=None, max_length=512)
    twitter_url: str | None = Field(default=None, max_length=512)
    company_size: str | None = None
    revenue: float | None = Field(default=None, ge=0)
    employee_count: int | None = Field(default=None, ge=0)
    owner_id: uuid.UUID | None = None
    tags: list[str] | None = None
    description: str | None = Field(default=None, max_length=5000)
    lead_score: float | None = Field(default=None, ge=0, le=100)
    is_favorite: bool | None = None
    is_archived: bool | None = None

    _validate_company_size = field_validator("company_size")(_validate_company_size)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in LEAD_STATUS_CHOICES:
            raise ValueError(f"Status must be one of: {', '.join(LEAD_STATUS_CHOICES)}.")
        return value


class NoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    is_pinned: bool = False


class NoteUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=10_000)
    is_pinned: bool | None = None


BulkActionType = Literal[
    "delete", "archive", "restore", "favorite", "unfavorite",
    "assign_owner", "change_status", "add_tags", "remove_tags",
]


class BulkLeadActionRequest(BaseModel):
    lead_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)
    action: BulkActionType
    owner_id: uuid.UUID | None = None
    status: str | None = None
    tags: list[str] | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in LEAD_STATUS_CHOICES:
            raise ValueError(f"Status must be one of: {', '.join(LEAD_STATUS_CHOICES)}.")
        return value


class ImportMapping(BaseModel):
    """csv_column -> Lead field name (one of LeadCreateRequest's field names)."""
    mapping: dict[str, str]


# ─── Responses ─────────────────────────────────────────────────────────────────

class TagResponse(BaseModel):
    id: str
    name: str
    color: str | None


class LeadOwnerResponse(BaseModel):
    id: str
    full_name: str
    email: str
    avatar_url: str | None


class LeadResponse(BaseModel):
    id: str
    organization_id: str
    first_name: str | None
    last_name: str | None
    full_name: str
    email: str | None
    phone: str | None
    job_title: str | None
    company_name: str | None
    website: str | None
    industry: str | None
    source: str | None
    status: str
    priority: int
    country: str | None
    state: str | None
    city: str | None
    address: LeadAddress | None
    linkedin_url: str | None
    twitter_url: str | None
    company_size: str | None
    revenue: float | None
    employee_count: int | None
    owner: LeadOwnerResponse | None
    tags: list[TagResponse]
    description: str | None
    lead_score: float | None
    notes_count: int
    attachments_count: int
    activities_count: int
    is_favorite: bool
    is_archived: bool
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class NoteResponse(BaseModel):
    id: str
    lead_id: str
    author_id: str | None
    author_name: str | None
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class AttachmentResponse(BaseModel):
    id: str
    lead_id: str
    filename: str
    file_url: str
    file_size: int | None
    mime_type: str | None
    uploaded_by: str | None
    uploaded_by_name: str | None
    created_at: datetime


class ActivityResponse(BaseModel):
    id: str
    lead_id: str
    actor_id: str | None
    actor_name: str | None
    activity_type: str
    summary: str | None
    metadata: dict | None
    occurred_at: datetime


class BulkActionError(BaseModel):
    lead_id: str
    message: str


class BulkActionResponse(BaseModel):
    action: str
    requested_count: int
    success_count: int
    failed_count: int
    errors: list[BulkActionError]


class ImportPreviewResponse(BaseModel):
    headers: list[str]
    sample_rows: list[dict[str, str]]
    suggested_mapping: dict[str, str]
    total_rows: int
    available_fields: list[str]


class ImportFailedRow(BaseModel):
    row_number: int
    errors: list[str]
    data: dict[str, str]


class ImportResultResponse(BaseModel):
    total_rows: int
    successful_count: int
    failed_count: int
    duplicate_count: int
    failed_rows: list[ImportFailedRow]
