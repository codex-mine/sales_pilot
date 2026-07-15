"""
Automation, Analytics, Administration, and Billing domains.

Grouped in one file for conciseness — in production each would be
in its own package (automation/models.py, analytics/models.py, etc.).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    AuditActionEnum, InvoiceStatusEnum, IntegrationTypeEnum,
    NotificationTypeEnum, PaymentStatusEnum, PlanIntervalEnum,
    ScheduledJobStatusEnum, SubscriptionStatusEnum,
    WorkflowExecutionStatusEnum, WorkflowStatusEnum,
)

if TYPE_CHECKING:
    from app.models.identity.models import Organization, User


# ═════════════════════════════════════════════════════════════════════════════
# AUTOMATION DOMAIN
# ═════════════════════════════════════════════════════════════════════════════

class Workflow(BaseModel):
    """
    A configurable automation workflow.

    Workflows are triggered by events (lead_imported, reply_received, etc.)
    and execute a series of steps. The trigger and steps are stored as JSONB
    to support arbitrary configurations without schema changes.

    Why JSONB for steps instead of a normalized table?
    Workflow steps are tightly coupled to the trigger definition and rarely
    queried individually. JSONB avoids a complex recursive table structure.
    For very complex workflows (V2), consider a WorkflowStep table.
    """
    __tablename__ = "workflows"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatusEnum] = mapped_column(
        String(20), default=WorkflowStatusEnum.DRAFT, nullable=False, index=True
    )
    trigger_event: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="e.g. 'lead.imported', 'email.replied', 'lead.status_changed'"
    )
    trigger_conditions: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Filter conditions for when this workflow fires"
    )
    steps: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Ordered list of action steps: [{'type': 'send_email', 'template_id': '...'}]"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    executions: Mapped[List["WorkflowExecution"]] = relationship(
        "WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_workflows_org_trigger", "organization_id", "trigger_event"),
    )


class WorkflowExecution(BaseModel):
    """Execution record for each time a Workflow fires."""
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    trigger_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    trigger_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[WorkflowExecutionStatusEnum] = mapped_column(
        String(20), default=WorkflowExecutionStatusEnum.PENDING, nullable=False, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    execution_log: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")

    __table_args__ = (
        Index("ix_workflow_executions_org", "organization_id"),
    )


class ScheduledJob(BaseModel):
    """
    Recurring scheduled jobs (daily summary, weekly reports, data cleanup).
    Not the same as Celery beat tasks — these are user-configurable schedules.
    """
    __tablename__ = "scheduled_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    cron_expression: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Cron expression: '0 9 * * 1-5' = 9am weekdays"
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    status: Mapped[ScheduledJobStatusEnum] = mapped_column(
        String(20), default=ScheduledJobStatusEnum.ACTIVE
    )
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS DOMAIN
# ═════════════════════════════════════════════════════════════════════════════

class Event(BaseModel):
    """
    Generic analytics event store. Append-only.

    Every significant user action and system event is written here.
    Used for dashboards, funnels, and AI training data.

    Why not use Activity for analytics?
    Activity is CRM-scoped (per Lead). Event is broader — it captures
    campaign-level, user-level, and system-level events that don't belong
    to a specific lead. Think of it as a simplified data warehouse event table.
    """
    __tablename__ = "events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_events_org_name_occurred", "organization_id", "event_name", "occurred_at"),
        Index("ix_events_entity", "entity_type", "entity_id"),
    )


class Metric(BaseModel):
    """
    Pre-aggregated metrics for fast dashboard queries.

    Computed by a daily analytics pipeline (Celery beat task).
    Avoids expensive GROUP BY queries on the Events table every dashboard load.

    metric_date + period define the time window:
    period: 'daily', 'weekly', 'monthly'
    """
    __tablename__ = "metrics"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Breakdown dimensions: {'industry': 'SaaS', 'country': 'US'}"
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "campaign_id", "metric_name", "metric_date", "period",
            name="uq_metric_org_campaign_name_date_period"
        ),
        Index("ix_metrics_org_date", "organization_id", "metric_date"),
        Index("ix_metrics_name", "metric_name"),
    )


class Report(BaseModel):
    """Saved report configurations for recurring or scheduled reports."""
    __tablename__ = "reports"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Report configuration: filters, columns, date range, grouping"
    )
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipients: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DashboardWidget(BaseModel):
    """User-configured dashboard widget."""
    __tablename__ = "dashboard_widgets"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position_x: Mapped[int] = mapped_column(Integer, default=0)
    position_y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=4)
    height: Mapped[int] = mapped_column(Integer, default=3)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ═════════════════════════════════════════════════════════════════════════════
# ADMINISTRATION DOMAIN
# ═════════════════════════════════════════════════════════════════════════════

class Notification(BaseModel):
    """
    In-app notifications for users.
    Separate from email notifications (which are handled by the email system).
    """
    __tablename__ = "notifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    notification_type: Mapped[NotificationTypeEnum] = mapped_column(
        String(50), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="notifications", foreign_keys=[user_id]
    )

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_org", "organization_id"),
    )


class APIKey(BaseModel):
    """
    API keys for programmatic access to SalesPilot.
    Keys are hashed (SHA-256); the plaintext is shown once at creation.
    """
    __tablename__ = "api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="First 8 chars of the key shown in UI for identification (e.g. 'sp_live_a')"
    )
    key_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True,
        comment="SHA-256 hash of the full key"
    )
    scopes: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        comment="Allowed scopes: ['leads:read', 'campaigns:write']"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_hash", "key_hash"),
    )


class Integration(BaseModel):
    """
    OAuth-based integrations with external services (Google Calendar, Outlook, etc.).
    Tokens are stored encrypted (application-level encryption, not DB-level).
    """
    __tablename__ = "integrations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="User-level integrations (calendar, email) vs org-level (CRM, Slack)"
    )
    integration_type: Mapped[IntegrationTypeEnum] = mapped_column(
        String(30), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    external_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_account_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="integrations")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "integration_type",
            name="uq_integration_org_user_type"
        ),
        Index("ix_integrations_type", "integration_type"),
    )


class AuditLog(BaseModel):
    """
    Immutable audit trail for security-sensitive and business-critical actions.

    This is separate from Activity (CRM timeline) and Event (analytics).
    AuditLog captures WHO did WHAT to WHICH record and WHEN.
    Used for compliance, security investigations, and dispute resolution.

    Rows are never updated or soft-deleted here.
    Hardware-level retention policies (S3 archive, partition pruning) handle
    long-term storage instead of application-level deletion.
    """
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for system actions"
    )
    actor_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Denormalized email snapshot (actor may be deleted later)"
    )
    action: Mapped[AuditActionEnum] = mapped_column(String(30), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changes: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Before/after diff: {'before': {...}, 'after': {...}}"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_logs_org_occurred", "organization_id", "occurred_at"),
        Index("ix_audit_logs_actor", "actor_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# BILLING DOMAIN
# ═════════════════════════════════════════════════════════════════════════════

class Plan(BaseModel):
    """
    Subscription plan definitions. Seeded at deploy time.
    is_active: False means the plan is no longer offered but existing subs continue.
    """
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Float, nullable=False)
    price_annual: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    features: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Feature flags and limits: {'leads_limit': 10000, 'ai_jobs_limit': 500}"
    )
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_id_annual: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(BaseModel):
    """
    Organization subscription to a Plan.
    One active subscription per organization at any time.
    Historical subscriptions are preserved (soft delete / cancelled status).
    """
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    status: Mapped[SubscriptionStatusEnum] = mapped_column(
        String(20), nullable=False, default=SubscriptionStatusEnum.TRIALING, index=True
    )
    interval: Mapped[PlanIntervalEnum] = mapped_column(String(10), nullable=False)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trial_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    seats: Mapped[int] = mapped_column(Integer, default=1)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="subscription")
    plan: Mapped["Plan"] = relationship("Plan")
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice", back_populates="subscription", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_subscriptions_org", "organization_id"),
        Index("ix_subscriptions_stripe_id", "stripe_subscription_id"),
    )


class Invoice(BaseModel):
    """Billing invoice from Stripe (mirrored locally for display and auditing)."""
    __tablename__ = "invoices"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    status: Mapped[InvoiceStatusEnum] = mapped_column(
        String(20), nullable=False, default=InvoiceStatusEnum.DRAFT, index=True
    )
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    invoice_pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="invoices"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="invoice", cascade="all, delete-orphan"
    )


class Payment(BaseModel):
    """Individual payment attempt record."""
    __tablename__ = "payments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[PaymentStatusEnum] = mapped_column(
        String(20), nullable=False, default=PaymentStatusEnum.PENDING, index=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="payments")


class UsageRecord(BaseModel):
    """
    Metered usage tracking for billing (AI jobs, emails sent, leads imported).
    Enables usage-based billing and plan limit enforcement.
    """
    __tablename__ = "usage_records"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="'ai_jobs', 'emails_sent', 'leads_imported', 'seats_used'"
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_to_stripe: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="usage_records"
    )

    __table_args__ = (
        Index("ix_usage_records_org_metric", "organization_id", "metric_name"),
        Index("ix_usage_records_period", "period_start", "period_end"),
    )
