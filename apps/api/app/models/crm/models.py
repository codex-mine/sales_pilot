"""
CRM Domain — Company, Contact, Lead, LeadScore, Tag, Note, Activity, Attachment.

Architecture decisions:
- Company and Contact are separate from Lead.
  A Company can have many Contacts; a Lead is a *sales opportunity* that
  links a Contact (the prospect) to a Company. This mirrors how HubSpot,
  Salesforce, and Apollo model their CRM data. It avoids denormalization
  (storing company info on every lead row) and allows re-use of company
  research across multiple leads at the same company.

- LeadScore is a separate table (not a column on Lead) because:
  1. The score is computed by an AI agent and changes over time.
  2. We keep a history of scores for trend analysis.
  3. The score has multiple sub-dimensions (intent, fit, urgency) that
     would pollute the Lead table.

- Activity is an append-only event log. We never update activities.
  This makes the timeline auditable and easy to stream in real time.

- Tags use a Tag + LeadTag junction pattern instead of a JSONB array
  because tags need to be filterable, countable, and renameable efficiently.

- Attachment references S3 object keys, not binary data. We never store
  files in PostgreSQL — that would destroy I/O performance at scale.
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

from app.models.base import Base, BaseModel
from app.models.enums import ActivityTypeEnum, CompanySizeEnum, CompanyStatusEnum, LeadStatusEnum

if TYPE_CHECKING:
    from app.models.identity.models import User, Organization
    from app.models.campaigns.models import CampaignLead
    from app.models.communication.models import Email, Meeting
    from app.models.ai.models import AIJob, AIOutput


# ─── Association Tables ───────────────────────────────────────────────────────

class LeadTag(Base):
    """M:M between Lead and Tag."""
    __tablename__ = "lead_tags"
    __table_args__ = (
        Index("ix_lead_tags_lead", "lead_id"),
        Index("ix_lead_tags_tag", "tag_id"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    tagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    tagged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CompanyTag(Base):
    """M:M between Company and Tag — reuses the same `tags` table as leads
    (Tag is organization-scoped, not lead-specific), so a tag created for a
    lead can be reused on a company and vice versa without duplication."""
    __tablename__ = "company_tags"
    __table_args__ = (
        Index("ix_company_tags_company", "company_id"),
        Index("ix_company_tags_tag", "tag_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    tagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    tagged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# ─── Core Tables ─────────────────────────────────────────────────────────────

class Company(BaseModel):
    """
    Represents a real-world business entity.

    company_research is stored in CompanyResearch (AI domain) to keep AI artifacts
    separate from CRM facts. This table stores what we *know* about the company
    from the user's input; CompanyResearch stores what the AI *discovered*.

    Why not store research here?
    Because AI research can be re-run, has versioning, and contains embeddings.
    Mixing that with CRM data creates a wide table that's hard to maintain.
    """
    __tablename__ = "companies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        comment="Normalized domain (no www) for deduplication"
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    facebook_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    instagram_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Structured street address: {line1, line2}. City/state/country/postal_code are separate columns."
    )
    employee_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Self-reported/researched real-world headcount — distinct from contact_count (CRM records on file)"
    )
    size_range: Mapped[Optional[CompanySizeEnum]] = mapped_column(String(20), nullable=True)
    annual_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False, comment="ISO 4217 code")
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[CompanyStatusEnum] = mapped_column(
        String(20), default=CompanyStatusEnum.PROSPECT, nullable=False, index=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    technologies: Mapped[Optional[list]] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Tech stack inferred from research (e.g. ['Salesforce', 'AWS'])"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan"
    )
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", back_populates="company"
    )
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary="company_tags", back_populates="companies")
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="company", cascade="all, delete-orphan"
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity", back_populates="company", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "domain", name="uq_company_org_domain"),
        Index("ix_companies_org_name", "organization_id", "name"),
        Index("ix_companies_org_owner", "organization_id", "owner_id"),
        Index("ix_companies_org_archived", "organization_id", "archived_at"),
    )

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class Contact(BaseModel):
    """
    A person at a Company. A Contact becomes a Lead when there is a sales
    opportunity — the Contact record persists beyond any single campaign.

    Design rationale: Separating Contact from Lead allows the same person
    to appear in multiple campaigns without data duplication.
    """
    __tablename__ = "contacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_valid: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="Result of email validation check (None = not yet checked)"
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_decision_maker: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False,
        comment="Simple active/inactive flag for the Company > Employees display; full contact lifecycle management belongs to the future Contacts module"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="contacts")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="contact")

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_contact_org_email"),
        Index("ix_contacts_org_company", "organization_id", "company_id"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Lead(BaseModel):
    """
    A sales opportunity. Links a Contact to a Company within a sales pipeline.

    Why does Lead reference both Contact and Company separately?
    Because a Contact might not always have a Company (indie freelancers),
    and a Company might exist before we identify the right Contact.
    Both FKs are nullable to support partial data imports.

    owner_id: The sales rep responsible for this lead.
    source: How the lead was acquired (CSV import, manual, API, etc.).
    status: Global pipeline stage (different from CampaignLead.status which
            is campaign-specific progress).
    """
    __tablename__ = "leads"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Core fields
    status: Mapped[LeadStatusEnum] = mapped_column(
        String(30), default=LeadStatusEnum.NEW, nullable=False, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Import source: csv, manual, api, linkedin, etc."
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="0-100 priority score; higher = more important"
    )

    # Denormalized convenience fields (synced from Contact/Company at import time)
    # These avoid joins on the hot path (list view, export, sequence builder).
    # They are refreshed whenever the linked Contact or Company is updated.
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Structured street address: {line1, line2, postal_code}. City/state/country are separate columns."
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_size: Mapped[Optional[CompanySizeEnum]] = mapped_column(
        String(20), nullable=True,
        comment="Denormalized from Company.size_range; free-standing when no linked Company"
    )
    revenue: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Denormalized from Company.annual_revenue"
    )
    employee_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Denormalized from Company.employee_count"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Simple, user-editable relevance score (0-100). Distinct from LeadScore
    # below, which is an append-only *history* of AI-computed multi-dimension
    # scores — this is the plain CRM-style single number shown in list/detail
    # views until an AI scoring job (future module) starts writing LeadScore
    # rows, at which point the UI can prefer the latest LeadScore instead.
    lead_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # AI-generated fields
    icp_match_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Ideal Customer Profile match score (0.0-1.0)"
    )
    buying_intent_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    custom_fields: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Organization-defined custom fields (dynamic schema)"
    )
    notes_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Quick inline note; structured notes go to the Note table"
    )

    # Timestamps
    contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    contact: Mapped[Optional["Contact"]] = relationship("Contact", back_populates="leads")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="leads")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary="lead_tags", back_populates="leads")
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="lead", cascade="all, delete-orphan"
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity", back_populates="lead", cascade="all, delete-orphan"
    )
    scores: Mapped[List["LeadScore"]] = relationship(
        "LeadScore", back_populates="lead", cascade="all, delete-orphan",
        order_by="LeadScore.scored_at.desc()"
    )
    campaign_leads: Mapped[List["CampaignLead"]] = relationship(
        "CampaignLead", back_populates="lead"
    )
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="lead")
    meetings: Mapped[List["Meeting"]] = relationship("Meeting", back_populates="lead")
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="lead", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_leads_org_status", "organization_id", "status"),
        Index("ix_leads_org_owner", "organization_id", "owner_id"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_org_archived", "organization_id", "is_archived"),
        Index("ix_leads_org_favorite", "organization_id", "is_favorite"),
    )

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part) or "Unknown"


class LeadScore(BaseModel):
    """
    Historical AI-generated scores for a lead.
    We never update scores — we insert new rows. This gives a scoring history
    useful for training future models and understanding score drift.
    """
    __tablename__ = "lead_scores"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    ai_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="SET NULL"),
        nullable=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    icp_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    buying_intent_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    urgency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    factors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="scores")

    __table_args__ = (
        Index("ix_lead_scores_lead_scored", "lead_id", "scored_at"),
    )


class Tag(BaseModel):
    """
    Organizational tags, shared across leads and companies. Tags are scoped
    to an organization, not to a single entity type.
    Using a proper Tag table (vs JSONB array) enables:
    - Fast filtering: WHERE EXISTS (SELECT 1 FROM lead_tags lt JOIN tags t ON ...)
    - Tag rename without touching every lead/company row
    - Tag analytics (most common tags, etc.)
    """
    __tablename__ = "tags"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True,
        comment="Hex color code e.g. #FF5733"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", secondary="lead_tags", back_populates="tags"
    )
    companies: Mapped[List["Company"]] = relationship(
        "Company", secondary="company_tags", back_populates="tags"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_tag_org_name"),
    )


class Note(BaseModel):
    """
    Structured notes on a Lead *or* a Company. Supports rich text (HTML
    stored as text). Notes are append-friendly but can be edited
    (updated_at tracks changes).

    lead_id/company_id are both nullable and mutually exclusive (exactly one
    is set) — this table started Lead-only; the Company module (CRM >
    Companies) reuses it instead of introducing a parallel CompanyNote table,
    per the "no duplicate logic" rule. Application code (NoteService) is
    responsible for setting exactly one anchor.
    """
    __tablename__ = "notes"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="notes")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="notes")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])


class Activity(BaseModel):
    """
    Append-only timeline of events for a Lead *or* a Company (mutually
    exclusive anchors — see Note's docstring for the same pattern/rationale).

    Why append-only? Because updating a single status field destroys history.
    With append-only events we can reconstruct the full timeline, compute
    time-to-open, time-to-reply, and feed data into analytics/ML pipelines.

    entity_type / entity_id allow linking to any related object (Email, Meeting, etc.)
    without a FK to every possible table.
    """
    __tablename__ = "activities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for system/AI-generated activities"
    )
    activity_type: Mapped[ActivityTypeEnum] = mapped_column(
        String(50), nullable=False, index=True
    )
    summary: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Polymorphic reference: 'email', 'meeting', 'note', etc."
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="ID of the referenced entity (no FK — polymorphic)"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="activities")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="activities")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("ix_activities_org_lead", "organization_id", "lead_id"),
        Index("ix_activities_org_company", "organization_id", "company_id"),
        Index("ix_activities_type_occurred", "activity_type", "occurred_at"),
        Index("ix_activities_entity", "entity_type", "entity_id"),
    )


class Attachment(BaseModel):
    """
    File attachments for leads *or* companies (call recordings, proposals,
    etc.). Files are stored on local disk via StorageService; this table
    stores the metadata. lead_id/company_id are mutually exclusive, mirroring
    Note/Activity's polymorphism.
    """
    __tablename__ = "attachments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_key: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="S3 object key"
    )
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="attachments")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="attachments")
    uploader: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by])
