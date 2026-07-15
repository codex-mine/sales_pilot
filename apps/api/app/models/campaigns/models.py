"""
Campaigns Domain — Campaign, CampaignLead, Sequence, SequenceStep, EmailTemplate.

Architecture decisions:
- Campaign → Sequence → SequenceStep is a strict hierarchy.
  A Campaign defines the "what" and "who"; a Sequence defines the "when" and "how".
  One campaign can have one active sequence (V1), multiple sequences (A/B, V2).

- CampaignLead tracks the per-lead progress through a campaign.
  This is the enrollment record — it stores where the lead is in the sequence
  and when the next action should fire. The Celery scheduler reads this table.

- EmailTemplate is decoupled from SequenceStep. A template is a reusable
  content asset; a step references a template. This allows templates to be
  shared across campaigns without copying.

- PromptTemplate (AI domain) generates EmailTemplate content.
  The separation is intentional: prompt engineering lives in the AI domain;
  marketing content lives in Campaigns.

- step_order uses an Integer, not a list position. This allows reordering
  without updating every subsequent row (just update the specific rows).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    CampaignLeadStatusEnum, CampaignStatusEnum,
    EmailTemplateTypeEnum, EmailToneEnum, SequenceStepTypeEnum,
)

if TYPE_CHECKING:
    from app.models.identity.models import User, Organization
    from app.models.crm.models import Lead
    from app.models.communication.models import Email


class Campaign(BaseModel):
    """
    A campaign represents a targeted outreach effort to a set of leads.
    Campaigns have a Sequence (the automation playbook) and an Audience (the leads).
    """
    __tablename__ = "campaigns"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatusEnum] = mapped_column(
        String(20), default=CampaignStatusEnum.DRAFT, nullable=False, index=True
    )
    goal: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
        comment="Human-readable campaign goal used by AI email generator"
    )
    target_industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_job_titles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    value_proposition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    daily_send_limit: Mapped[int] = mapped_column(
        Integer, default=50,
        comment="Max emails to send per day (rate limiting)"
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    send_days: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Days of week to send: ['monday', 'tuesday', ...]"
    )
    send_start_hour: Mapped[int] = mapped_column(
        Integer, default=9,
        comment="Start hour in local timezone (0-23)"
    )
    send_end_hour: Mapped[int] = mapped_column(
        Integer, default=17,
        comment="End hour in local timezone (0-23)"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    sequences: Mapped[List["Sequence"]] = relationship(
        "Sequence", back_populates="campaign", cascade="all, delete-orphan"
    )
    campaign_leads: Mapped[List["CampaignLead"]] = relationship(
        "CampaignLead", back_populates="campaign", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_campaigns_org_status", "organization_id", "status"),
    )


class Sequence(BaseModel):
    """
    An ordered series of steps (emails, waits, tasks) for a campaign.
    V1: one sequence per campaign. V2: multiple sequences for A/B testing.
    """
    __tablename__ = "sequences"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="sequences")
    steps: Mapped[List["SequenceStep"]] = relationship(
        "SequenceStep", back_populates="sequence",
        cascade="all, delete-orphan",
        order_by="SequenceStep.step_order"
    )
    campaign_leads: Mapped[List["CampaignLead"]] = relationship(
        "CampaignLead", back_populates="sequence"
    )


class SequenceStep(BaseModel):
    """
    A single step in a sequence (email, wait day, LinkedIn message, task).

    delay_days: how many days after the previous step to execute this step.
    step_order: position in the sequence (1-indexed, allows gaps for reordering).
    condition: optional JSON rule for conditional branching (e.g. "only if not opened").
    """
    __tablename__ = "sequence_steps"

    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    email_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True
    )
    step_type: Mapped[SequenceStepTypeEnum] = mapped_column(
        String(30), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Days after previous step before this step executes"
    )
    delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    subject_override: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
        comment="Override the template subject for this step"
    )
    body_override: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Override the template body for this step"
    )
    condition: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Conditional execution rules: {'skip_if': 'opened', 'only_if': 'not_replied'}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    sequence: Mapped["Sequence"] = relationship("Sequence", back_populates="steps")
    email_template: Mapped[Optional["EmailTemplate"]] = relationship("EmailTemplate")
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="sequence_step")

    __table_args__ = (
        UniqueConstraint("sequence_id", "step_order", name="uq_step_sequence_order"),
        Index("ix_sequence_steps_sequence", "sequence_id"),
    )


class EmailTemplate(BaseModel):
    """
    Reusable email content. Templates support variable interpolation using
    Jinja2 syntax: {{ lead.first_name }}, {{ company.name }}, etc.

    ai_generated: True if the AI wrote this template (stores the AI job reference).
    Why keep AI-generated and human-written templates in the same table?
    Because from a usage perspective they are identical — both can be edited,
    selected, and assigned to steps.
    """
    __tablename__ = "email_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ai_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="SET NULL"), nullable=True,
        comment="Reference to AI job that generated this template"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[EmailTemplateTypeEnum] = mapped_column(
        String(30), nullable=False, index=True
    )
    tone: Mapped[Optional[EmailToneEnum]] = mapped_column(String(20), nullable=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Plain-text fallback for email clients that don't render HTML"
    )
    ai_reasoning: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="AI explanation of why this email was written this way (for user learning)"
    )
    variables_used: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="List of template variables: ['first_name', 'company_name', ...]"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1,
        comment="Manual version counter for template edits"
    )

    # Performance analytics (denormalized for fast template comparison)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_opened: Mapped[int] = mapped_column(Integer, default=0)
    total_replied: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_email_templates_org_type", "organization_id", "template_type"),
    )


class CampaignLead(BaseModel):
    """
    Enrollment record: a Lead enrolled in a Campaign via a Sequence.

    This is the table the Celery scheduler queries to determine what to send next.
    next_step_id: the SequenceStep to execute next.
    next_action_at: when to execute it (computed after each step completes).

    Why a separate table instead of a column on Lead?
    A lead can be in multiple campaigns simultaneously. CampaignLead is the
    many-to-many table between Lead and Campaign with rich enrollment state.
    """
    __tablename__ = "campaign_leads"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sequence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="SET NULL"),
        nullable=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    status: Mapped[CampaignLeadStatusEnum] = mapped_column(
        String(20), default=CampaignLeadStatusEnum.ENROLLED, nullable=False, index=True
    )
    current_step_order: Mapped[int] = mapped_column(Integer, default=0)
    next_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequence_steps.id", ondelete="SET NULL"),
        nullable=True
    )
    next_action_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
        comment="When Celery should execute the next step for this lead"
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opted_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="campaign_leads")
    lead: Mapped["Lead"] = relationship("Lead", back_populates="campaign_leads")
    sequence: Mapped[Optional["Sequence"]] = relationship("Sequence", back_populates="campaign_leads")
    next_step: Mapped[Optional["SequenceStep"]] = relationship(
        "SequenceStep", foreign_keys=[next_step_id]
    )
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="campaign_lead")

    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
        Index("ix_campaign_leads_next_action", "next_action_at", "status"),
        Index("ix_campaign_leads_org", "organization_id"),
    )
