"""Request/response schemas for AI Personalized Email Generation & Human
Review (Leads -> Outreach, Email Templates). Trigger endpoints return
`AIJobResponse` (app.schemas.ai) directly, same as the Research module — the
frontend hands the id straight to the existing `useAIJob` poller and reads
generated variants off `job.outputs` (AIOutput rows, `output_type=
"email_variant"`), never a bespoke shape."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import EmailTemplateTypeEnum, EmailToneEnum


class GenerateEmailRequest(BaseModel):
    template_type: EmailTemplateTypeEnum
    tone: EmailToneEnum
    variant_count: int = Field(default=2, ge=1, le=3)
    custom_instruction: str | None = Field(default=None, max_length=2000)


class RegenerateEmailRequest(BaseModel):
    source_output_id: uuid.UUID
    custom_instruction: str = Field(min_length=1, max_length=2000)
    template_type: EmailTemplateTypeEnum | None = None
    tone: EmailToneEnum | None = None
    variant_count: int = Field(default=2, ge=1, le=3)


class ApproveEmailVariantRequest(BaseModel):
    edited_subject: str | None = Field(default=None, max_length=512)
    edited_body_html: str | None = None
    edited_body_text: str | None = None
    save_as_template: bool = False
    template_name: str | None = Field(default=None, max_length=255)
    from_email: EmailStr
    from_name: str | None = Field(default=None, max_length=255)


class BulkLeadEmailGenerationRequest(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=200)
    template_type: EmailTemplateTypeEnum
    tone: EmailToneEnum
    variant_count: int = Field(default=2, ge=1, le=3)


class BulkEmailGenerationResponse(BaseModel):
    requested_count: int
    queued_count: int
    errors: list[str]


class EmailResponse(BaseModel):
    id: str
    lead_id: str
    from_email: str
    from_name: str | None
    to_email: str
    to_name: str | None
    subject: str
    body_html: str
    body_text: str | None
    current_status: str
    ai_generated: bool
    personalization_data: dict | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    created_at: datetime


def _validate_template_type(value: str | None) -> str | None:
    if value is not None and value not in {e.value for e in EmailTemplateTypeEnum}:
        raise ValueError(f"template_type must be one of: {', '.join(e.value for e in EmailTemplateTypeEnum)}.")
    return value


def _validate_tone(value: str | None) -> str | None:
    if value is not None and value not in {e.value for e in EmailToneEnum}:
        raise ValueError(f"tone must be one of: {', '.join(e.value for e in EmailToneEnum)}.")
    return value


class EmailTemplateCreateRequest(BaseModel):
    """Manual (non-AI) template creation — Phase X Issue 07. `template_type`
    doubles as the "category" the feature asks for (COLD_OUTREACH/FOLLOW_UP/
    BREAK_UP/LINKEDIN/MEETING_REQUEST/PROPOSAL/CUSTOM — `CUSTOM` fits a
    template that doesn't map to any of the campaign-oriented types), so no
    separate category field/column was needed."""

    name: str = Field(min_length=1, max_length=255)
    template_type: str
    tone: str | None = None
    subject: str = Field(min_length=1, max_length=512)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    variables_used: list[str] | None = None
    is_active: bool = True

    _validate_template_type = field_validator("template_type")(_validate_template_type)
    _validate_tone = field_validator("tone")(_validate_tone)


class EmailTemplateUpdateRequest(BaseModel):
    """PATCH semantics — template_type/tone stay plain strings (not the enum
    types), matching LeadUpdateRequest.status/CompanyUpdateRequest.status."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    template_type: str | None = None
    tone: str | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=512)
    body_html: str | None = Field(default=None, min_length=1)
    body_text: str | None = None
    variables_used: list[str] | None = None
    is_active: bool | None = None

    _validate_template_type = field_validator("template_type")(_validate_template_type)
    _validate_tone = field_validator("tone")(_validate_tone)


class DuplicateEmailTemplateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class EmailTemplateResponse(BaseModel):
    id: str
    organization_id: str
    ai_job_id: str | None
    name: str
    template_type: str
    tone: str | None
    subject: str
    body_html: str
    body_text: str | None
    ai_reasoning: str | None
    variables_used: list[str] | None
    is_active: bool
    is_ai_generated: bool
    version: int
    total_sent: int
    total_opened: int
    total_replied: int
    created_at: datetime
    updated_at: datetime
