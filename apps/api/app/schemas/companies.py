"""Request/response schemas for the Company module (CRM -> Companies)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import CompanySizeEnum, CompanyStatusEnum

COMPANY_STATUS_CHOICES: list[str] = [status.value for status in CompanyStatusEnum]
COMPANY_SIZE_CHOICES: list[str] = [size.value for size in CompanySizeEnum]


class CompanyAddress(BaseModel):
    line1: str | None = Field(default=None, max_length=255)
    line2: str | None = Field(default=None, max_length=255)


def _validate_company_size(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in COMPANY_SIZE_CHOICES:
        raise ValueError(f"Company size must be one of: {', '.join(COMPANY_SIZE_CHOICES)}.")
    return value


def _validate_status(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in COMPANY_STATUS_CHOICES:
        raise ValueError(f"Status must be one of: {', '.join(COMPANY_STATUS_CHOICES)}.")
    return value


# ─── Requests ──────────────────────────────────────────────────────────────────

class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    size_range: str | None = None
    annual_revenue: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    address: CompanyAddress | None = None
    linkedin_url: str | None = Field(default=None, max_length=512)
    twitter_url: str | None = Field(default=None, max_length=512)
    facebook_url: str | None = Field(default=None, max_length=512)
    instagram_url: str | None = Field(default=None, max_length=512)
    status: str = Field(default=CompanyStatusEnum.PROSPECT.value)
    owner_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)

    _validate_company_size = field_validator("size_range")(_validate_company_size)
    _validate_status = field_validator("status")(_validate_status)


class CompanyUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    size_range: str | None = None
    annual_revenue: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    address: CompanyAddress | None = None
    linkedin_url: str | None = Field(default=None, max_length=512)
    twitter_url: str | None = Field(default=None, max_length=512)
    facebook_url: str | None = Field(default=None, max_length=512)
    instagram_url: str | None = Field(default=None, max_length=512)
    status: str | None = None
    owner_id: uuid.UUID | None = None
    tags: list[str] | None = None

    _validate_company_size = field_validator("size_range")(_validate_company_size)
    _validate_status = field_validator("status")(_validate_status)


BulkCompanyActionType = Literal[
    "delete", "archive", "restore", "assign_owner", "change_status", "add_tags", "remove_tags",
]


class BulkCompanyActionRequest(BaseModel):
    company_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)
    action: BulkCompanyActionType
    owner_id: uuid.UUID | None = None
    status: str | None = None
    tags: list[str] | None = None

    _validate_status = field_validator("status")(_validate_status)


# ─── Responses ─────────────────────────────────────────────────────────────────

class CompanyTagResponse(BaseModel):
    id: str
    name: str
    color: str | None


class CompanyOwnerResponse(BaseModel):
    id: str
    full_name: str
    email: str
    avatar_url: str | None


class CompanyResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    legal_name: str | None
    logo_url: str | None
    website: str | None
    domain: str | None
    industry: str | None
    description: str | None
    phone: str | None
    email: str | None
    founded_year: int | None
    size_range: str | None
    employee_count: int | None
    annual_revenue: float | None
    currency: str
    country: str | None
    state: str | None
    city: str | None
    postal_code: str | None
    address: CompanyAddress | None
    linkedin_url: str | None
    twitter_url: str | None
    facebook_url: str | None
    instagram_url: str | None
    status: str
    owner: CompanyOwnerResponse | None
    tags: list[CompanyTagResponse]
    contact_count: int
    lead_count: int
    notes_count: int
    attachments_count: int
    is_archived: bool
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class CompanyNoteResponse(BaseModel):
    id: str
    company_id: str
    author_id: str | None
    author_name: str | None
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class CompanyAttachmentResponse(BaseModel):
    id: str
    company_id: str
    filename: str
    file_url: str
    file_size: int | None
    mime_type: str | None
    uploaded_by: str | None
    uploaded_by_name: str | None
    created_at: datetime


class CompanyActivityResponse(BaseModel):
    id: str
    company_id: str
    actor_id: str | None
    actor_name: str | None
    activity_type: str
    summary: str | None
    metadata: dict | None
    occurred_at: datetime


class CompanyEmployeeResponse(BaseModel):
    """Read-only view over `Contact` rows linked to a company — full employee
    management is deferred to the future Contacts module (per spec). No
    dedicated avatar image exists on Contact yet, so the frontend renders an
    initials avatar from `full_name`, same as it does for Leads."""
    id: str
    full_name: str
    job_title: str | None
    department: str | None
    email: str
    phone: str | None
    status: str
    is_decision_maker: bool | None
    has_linked_lead: bool
    last_activity_at: datetime
    created_at: datetime


class BulkActionError(BaseModel):
    company_id: str
    message: str


class BulkActionResponse(BaseModel):
    action: str
    requested_count: int
    success_count: int
    failed_count: int
    errors: list[BulkActionError]
