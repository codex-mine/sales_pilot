"""
Request/response schemas for the Organization module (CRM -> Organizations).

Kept in a dedicated file rather than folded into schemas/auth.py: auth.py's
`OrganizationResponse` is the minimal shape embedded in `/auth/me` and is left
untouched (other code depends on its exact fields) — this module's
`OrganizationDetailResponse` is the richer shape for the dedicated
Organizations screens.
"""

import re
import uuid
from datetime import datetime
from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_LANGUAGE_RE = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_COMPANY_SIZES = {"1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"}
_TIMEZONES = available_timezones()


def _validate_slug(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip().lower()
    if not _SLUG_RE.match(value):
        raise ValueError(
            "Slug must be lowercase letters, numbers, and hyphens only (no leading/trailing/double hyphens)."
        )
    return value


def _validate_timezone(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in _TIMEZONES:
        raise ValueError(f"'{value}' is not a recognized IANA timezone.")
    return value


def _validate_language(value: str | None) -> str | None:
    if value is None:
        return value
    if not _LANGUAGE_RE.match(value):
        raise ValueError("Language must be a BCP-47-style code, e.g. 'en' or 'en-US'.")
    return value


def _validate_currency(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.upper()
    if not _CURRENCY_RE.match(value):
        raise ValueError("Currency must be a 3-letter ISO 4217 code, e.g. 'USD'.")
    return value


def _validate_brand_color(value: str | None) -> str | None:
    if value is None:
        return value
    if not _HEX_COLOR_RE.match(value):
        raise ValueError("Brand color must be a hex color, e.g. '#16A34A'.")
    return value


def _validate_company_size(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in _COMPANY_SIZES:
        raise ValueError(f"Company size must be one of: {', '.join(sorted(_COMPANY_SIZES))}.")
    return value


class OrganizationAddress(BaseModel):
    line1: str | None = Field(default=None, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)


# ─── Requests ──────────────────────────────────────────────────────────────────

class OrganizationCreateRequest(BaseModel):
    """
    Accepted for REST completeness, but the current data model gives every
    user exactly one organization (assigned at registration) — this route
    always responds 409. See `OrganizationService.create_additional` docstring.
    """
    name: str = Field(min_length=1, max_length=255)


class OrganizationUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics, only supplied fields change."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    website: str | None = Field(default=None, max_length=512)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    company_size: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    timezone: str | None = None
    language: str | None = None
    currency: str | None = None
    brand_color: str | None = None
    address: OrganizationAddress | None = None

    _validate_slug = field_validator("slug")(_validate_slug)
    _validate_timezone = field_validator("timezone")(_validate_timezone)
    _validate_language = field_validator("language")(_validate_language)
    _validate_currency = field_validator("currency")(_validate_currency)
    _validate_brand_color = field_validator("brand_color")(_validate_brand_color)
    _validate_company_size = field_validator("company_size")(_validate_company_size)

    @field_validator("website")
    @classmethod
    def _validate_website(cls, value: str | None) -> str | None:
        if value and not re.match(r"^https?://", value):
            raise ValueError("Website must start with http:// or https://.")
        return value


# ─── Responses ─────────────────────────────────────────────────────────────────

class OrganizationDetailResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: str | None
    logo_url: str | None
    website: str | None
    email: str | None
    phone: str | None
    industry: str | None
    country: str | None
    company_size: str | None
    timezone: str
    language: str
    currency: str
    brand_color: str | None
    description: str | None
    address: OrganizationAddress | None
    is_active: bool
    member_count: int
    created_at: datetime
    updated_at: datetime


class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    avatar_url: str | None
    role: str | None
    status: str
    email_verified: bool
    joined_at: datetime
    last_active_at: datetime | None
