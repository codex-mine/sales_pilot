"""Request/response schemas for the AI Provider Foundation module (AI ->
Agents / Jobs / Outputs / Prompts / Settings)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AIAgentTypeEnum, LLMProviderEnum

AI_JOB_STATUS_CHOICES = ["pending", "running", "completed", "failed", "retrying", "cancelled"]


# ─── Agents ────────────────────────────────────────────────────────────────────

class AIAgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    agent_type: AIAgentTypeEnum
    description: str | None = Field(default=None, max_length=2000)
    provider: LLMProviderEnum = LLMProviderEnum.ANTHROPIC
    model_name: str = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=200_000)
    prompt_template_id: uuid.UUID | None = None
    is_active: bool = True
    config: dict | None = None


class AIAgentUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics. agent_type is immutable (it is
    the org-unique key)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    provider: LLMProviderEnum | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)
    prompt_template_id: uuid.UUID | None = None
    is_active: bool | None = None
    config: dict | None = None


class AIAgentResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    agent_type: str
    description: str | None
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    prompt_template_id: str | None
    prompt_template_name: str | None
    is_active: bool
    config: dict | None
    created_at: datetime
    updated_at: datetime


# ─── Jobs / outputs ────────────────────────────────────────────────────────────

class AIOutputResponse(BaseModel):
    id: str
    job_id: str
    output_type: str
    content_text: str | None
    content_json: dict | list | None
    is_approved: bool | None
    approved_by: str | None
    approved_at: datetime | None
    quality_score: float | None
    created_at: datetime


class AIJobResponse(BaseModel):
    id: str
    organization_id: str
    agent_id: str | None
    agent_type: str | None
    parent_job_id: str | None
    initiated_by: str | None
    entity_type: str | None
    entity_id: str | None
    job_type: str
    status: str
    provider: str | None
    model_name: str | None
    prompt_version_id: str | None
    input_data: dict | None
    error_message: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    latency_ms: int | None
    retry_count: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    outputs: list[AIOutputResponse]


class AIJobListItemResponse(BaseModel):
    """Trimmed row for the history table — no input_data payload (it can be
    large; the detail endpoint carries it)."""
    id: str
    job_type: str
    status: str
    entity_type: str | None
    entity_id: str | None
    provider: str | None
    model_name: str | None
    total_tokens: int | None
    cost_usd: float | None
    latency_ms: int | None
    retry_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# ─── Prompts ───────────────────────────────────────────────────────────────────

class PromptTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    agent_type: AIAgentTypeEnum | None = None
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str = Field(min_length=1)
    user_prompt_template: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)


class PromptTemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class PromptVersionCreateRequest(BaseModel):
    system_prompt: str = Field(min_length=1)
    user_prompt_template: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    provider: LLMProviderEnum | None = None
    model_name: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    change_notes: str | None = Field(default=None, max_length=2000)
    activate: bool = False


class PromptVersionResponse(BaseModel):
    id: str
    template_id: str
    version_number: int
    system_prompt: str
    user_prompt_template: str
    variables: list[str]
    provider: str | None
    model_name: str | None
    temperature: float | None
    change_notes: str | None
    is_active: bool
    total_uses: int
    created_at: datetime


class PromptTemplateResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    agent_type: str | None
    description: str | None
    is_system: bool
    active_version_id: str | None
    active_version_number: int | None
    version_count: int
    created_at: datetime
    updated_at: datetime


# ─── Settings / usage ──────────────────────────────────────────────────────────

class AIProviderStatusResponse(BaseModel):
    provider: str
    integration_type: str
    has_key: bool
    has_org_key: bool
    has_platform_fallback: bool


class AISettingsResponse(BaseModel):
    providers: list[AIProviderStatusResponse]
    default_provider: str
    default_model: str


class AISettingsUpdateRequest(BaseModel):
    provider: LLMProviderEnum
    api_key: str | None = Field(default=None, min_length=1, max_length=512)
    base_url: str | None = Field(default=None, max_length=512)
    # remove=True deletes the stored org-level credential for the provider.
    remove: bool = False


class AIUsageByJobTypeResponse(BaseModel):
    job_type: str
    job_count: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: int


class AIDailyCostResponse(BaseModel):
    date: str
    cost_usd: float


class AIUsageResponse(BaseModel):
    window_days: int
    total_cost_usd: float
    total_jobs: int
    total_tokens: int
    all_time_cost_usd: float
    by_job_type: list[AIUsageByJobTypeResponse]
    daily_costs: list[AIDailyCostResponse]
