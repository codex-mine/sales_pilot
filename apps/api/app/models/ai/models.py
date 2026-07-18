"""
AI Domain — AIAgent, AIJob, AIOutput, AIMemory, PromptTemplate, PromptVersion,
            CompanyResearch, ProspectAnalysis.

Architecture decisions:
- AIJob is the central execution record. Every AI invocation creates a Job.
  Jobs are never overwritten — each run is a separate row with full metadata
  (tokens used, cost, latency, model, provider). This enables:
  1. Cost tracking per organization
  2. Debugging failed jobs
  3. Replayability (retry with same inputs)
  4. Historical comparison across model versions

- AIOutput stores the structured result of a job separately from the job metadata.
  Why separate? Because outputs can be large (full email bodies, research reports)
  and we may want to retrieve them independently. Also, one job can produce
  multiple outputs (e.g., generate 3 email variants → 3 AIOutput rows).

- PromptTemplate + PromptVersion follows the same pattern as git branching:
  a template is the conceptual prompt; versions are immutable snapshots.
  We never edit a PromptVersion — we create new versions. This allows A/B
  testing of prompts and regression testing after model upgrades.

- AIMemory provides agent memory for contextual recall.
  Uses pgvector for semantic similarity search. The ChromaDB mentioned in the
  spec can be used as an external store; this table acts as the relational
  cache/index for querying memories by lead/company/organization.

- CompanyResearch and ProspectAnalysis are domain-specific AI outputs with
  typed schemas. They exist as separate tables (not just generic AIOutput)
  because they have many structured fields queried individually (industry,
  pain_points, etc.). Generic AIOutput handles unstructured text outputs.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AIAgentTypeEnum, AIJobStatusEnum, LLMProviderEnum

# pgvector import — requires the pgvector SQLAlchemy extension
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

if TYPE_CHECKING:
    from app.models.identity.models import Organization, User
    from app.models.crm.models import Lead, Company


class AIAgent(BaseModel):
    """
    Definition of an AI agent. Think of this as the agent's "profile" —
    its purpose, which LLM it uses, and its system prompt (via PromptTemplate).

    Why a table for agents?
    Because organizations should be able to configure their agents (choose provider,
    tune temperature, change the default prompt template) without code deployments.
    This table makes agents configurable at runtime.
    """
    __tablename__ = "ai_agents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[AIAgentTypeEnum] = mapped_column(
        String(30), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[LLMProviderEnum] = mapped_column(
        String(20), default=LLMProviderEnum.OPENAI, nullable=False
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="e.g. gpt-4o, claude-3-5-sonnet, llama-3.1-70b"
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    prompt_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Agent-specific config: tools, retrieval strategy, etc."
    )

    # Relationships
    prompt_template: Mapped[Optional["PromptTemplate"]] = relationship("PromptTemplate")
    jobs: Mapped[List["AIJob"]] = relationship("AIJob", back_populates="agent")

    __table_args__ = (
        UniqueConstraint("organization_id", "agent_type", name="uq_agent_org_type"),
    )


class AIJob(BaseModel):
    """
    Execution record for every AI agent invocation.

    This is the central audit table for all AI activity. Never update rows;
    always insert new ones for retries.

    input_data: the full input payload sent to the LLM (for replay/debugging).
    error_message: populated only on failure.
    retry_count: incremented by the Celery retry mechanism.
    parent_job_id: supports orchestrator → sub-agent job trees.
    """
    __tablename__ = "ai_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_agents.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    parent_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Orchestrator job that spawned this child job"
    )
    initiated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL if triggered automatically by a workflow or scheduler"
    )

    # What this job is working on
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="The type of entity: 'lead', 'company', 'campaign', etc."
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="The ID of the entity being processed"
    )
    job_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="e.g. 'research_company', 'generate_email', 'classify_reply'"
    )

    # Execution
    status: Mapped[AIJobStatusEnum] = mapped_column(
        String(20), default=AIJobStatusEnum.PENDING, nullable=False, index=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # LLM details
    provider: Mapped[Optional[LLMProviderEnum]] = mapped_column(String(20), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Inputs / Outputs / Errors
    input_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Full input payload for replay/debugging. Consider encryption for PII."
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cost / Performance tracking
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Estimated cost in USD based on provider pricing"
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    agent: Mapped[Optional["AIAgent"]] = relationship("AIAgent", back_populates="jobs")
    outputs: Mapped[List["AIOutput"]] = relationship(
        "AIOutput", back_populates="job", cascade="all, delete-orphan"
    )
    child_jobs: Mapped[List["AIJob"]] = relationship(
        "AIJob", foreign_keys=[parent_job_id]
    )

    __table_args__ = (
        Index("ix_ai_jobs_org_status", "organization_id", "status"),
        Index("ix_ai_jobs_entity", "entity_type", "entity_id"),
        Index("ix_ai_jobs_created_at", "created_at"),
    )


class AIOutput(BaseModel):
    """
    The structured or unstructured output of an AIJob.

    Why not store output on AIJob directly?
    1. A single job can produce multiple outputs (3 email variants).
    2. Outputs can be large — separating them keeps the AIJob table lean for analytics.
    3. Outputs can be approved/rejected individually.

    output_type: categorizes the output for downstream processing
    ('email', 'research_summary', 'reply_classification', etc.)
    """
    __tablename__ = "ai_outputs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    output_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict | list]] = mapped_column(
        JSONB, nullable=True,
        comment="Object for single-result outputs (research, analysis); array for "
        "multi-variant outputs (email generation's 2-3 subject/body variants)."
    )
    is_approved: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="NULL = pending review; True = approved; False = rejected"
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="AI self-rated quality score (0.0-1.0)"
    )

    # Relationships
    job: Mapped["AIJob"] = relationship("AIJob", back_populates="outputs")

    __table_args__ = (
        Index("ix_ai_outputs_job_type", "job_id", "output_type"),
    )


class CompanyResearch(BaseModel):
    """
    AI-researched information about a Company.

    Stored separately from the Company record for several reasons:
    1. It's AI-generated (not user-provided fact)
    2. It can be re-generated (multiple versions over time)
    3. It contains embedding vectors for similarity search
    4. It may be large (full research report as JSON)

    company_id is unique because we keep only the LATEST research per company.
    For historical versions, query AIJob with entity_type='company'.
    """
    __tablename__ = "company_research"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    ai_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Structured research fields
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    products_services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    target_customers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    technologies: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    competitors: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recent_news: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    pain_points: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Inferred pain points that our product/service can address"
    )
    sales_opportunities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    estimated_revenue: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    funding_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    growth_signals: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Full raw research for display
    raw_research: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    researched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Embedding for semantic search (requires pgvector)
    # embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    # Commented out for systems without pgvector — uncomment when extension is enabled.

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_company_research_company"),
        Index("ix_company_research_org", "organization_id"),
    )


class ProspectAnalysis(BaseModel):
    """
    AI analysis of a Lead/Contact as a sales prospect.

    Unlike CompanyResearch (which is about the company), ProspectAnalysis
    is about the individual person — their likely goals, buying authority,
    objections, and recommended approach.
    """
    __tablename__ = "prospect_analyses"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    ai_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="SET NULL"), nullable=True
    )
    buying_intent: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="high | medium | low"
    )
    priority_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_proposition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    predicted_objections: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    likely_goals: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    decision_authority: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="decision_maker | influencer | evaluator | end_user"
    )
    best_contact_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    analysed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("lead_id", name="uq_prospect_analysis_lead"),
    )


class PromptTemplate(BaseModel):
    """
    A named prompt template used by AI agents.
    Templates are versioned — use PromptVersion for the actual content.
    """
    __tablename__ = "prompt_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[Optional[AIAgentTypeEnum]] = mapped_column(String(30), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="System prompts are seeded and cannot be deleted"
    )
    active_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="FK to the currently active PromptVersion (set after FK is created)"
    )

    # Relationships
    versions: Mapped[List["PromptVersion"]] = relationship(
        "PromptVersion", back_populates="template",
        cascade="all, delete-orphan",
        foreign_keys="PromptVersion.template_id"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_prompt_template_org_name"),
    )


class PromptVersion(BaseModel):
    """
    Immutable snapshot of a PromptTemplate at a point in time.

    Why immutable? Because we need to:
    1. Know exactly which prompt produced which output (for debugging)
    2. Roll back to a previous version if a new prompt regresses
    3. Compare performance across prompt versions

    system_prompt: The system message given to the LLM.
    user_prompt_template: Jinja2 template for the user message.
    variables: List of variable names expected in the template.
    """
    __tablename__ = "prompt_versions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    provider: Mapped[Optional[LLMProviderEnum]] = mapped_column(String(20), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance stats (updated by analytics pipeline, not on every run)
    avg_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_uses: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    template: Mapped["PromptTemplate"] = relationship(
        "PromptTemplate", back_populates="versions", foreign_keys=[template_id]
    )

    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_prompt_version"),
        Index("ix_prompt_versions_template", "template_id"),
    )


class AIMemory(BaseModel):
    """
    Agent memory store for contextual recall across conversations.

    Why SQL instead of pure ChromaDB/vector store?
    The relational columns (organization_id, lead_id, agent_type, memory_type)
    allow fast filtered retrieval before the vector similarity step.
    Pattern: filter by organization + entity, then rank by vector similarity.

    ChromaDB/pgvector holds the vectors; this table holds the metadata + text.
    The external ChromaDB collection can be keyed by (organization_id, memory_type).
    """
    __tablename__ = "ai_memories"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    agent_type: Mapped[Optional[AIAgentTypeEnum]] = mapped_column(String(30), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="'lead', 'company', 'campaign', 'organization'"
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    memory_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="'interaction', 'preference', 'fact', 'instruction'"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    chroma_doc_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="ChromaDB document ID for the embedding of this memory"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Optional expiry; NULL = permanent memory"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_ai_memories_org_entity", "organization_id", "entity_type", "entity_id"),
        Index("ix_ai_memories_type", "memory_type"),
        Index("ix_ai_memories_expires", "expires_at"),
    )
