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


class EmailTemplateUpdateRequest(BaseModel):
    """PATCH semantics — template_type/tone stay plain strings (not the enum
    types), matching LeadUpdateRequest.status/CompanyUpdateRequest.status."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    template_type: str | None = None
    tone: str | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=512)
    body_html: str | None = Field(default=None, min_length=1)
    body_text: str | None = None
    is_active: bool | None = None

    @field_validator("template_type")
    @classmethod
    def _validate_template_type(cls, value: str | None) -> str | None:
        if value is not None and value not in {e.value for e in EmailTemplateTypeEnum}:
            raise ValueError(f"template_type must be one of: {', '.join(e.value for e in EmailTemplateTypeEnum)}.")
        return value

    @field_validator("tone")
    @classmethod
    def _validate_tone(cls, value: str | None) -> str | None:
        if value is not None and value not in {e.value for e in EmailToneEnum}:
            raise ValueError(f"tone must be one of: {', '.join(e.value for e in EmailToneEnum)}.")
        return value


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
