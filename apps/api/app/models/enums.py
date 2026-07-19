"""
Centralized enum definitions for SalesPilot AI.

All enums are defined here to prevent circular imports and to give a single
source of truth for valid state values. PostgreSQL native ENUMs are used for
columns that are frequently filtered/sorted — they are indexed more efficiently
than VARCHAR with a CHECK constraint, and they enforce data integrity at the DB level.

Naming convention: <Domain><Field>Enum  e.g. LeadStatusEnum, EmailEventTypeEnum
"""

import enum

# ─── Identity ────────────────────────────────────────────────────────────────


class UserStatusEnum(str, enum.Enum):
    """
    Account status gate for login. PENDING_VERIFICATION and ACTIVE allow login
    (email verification is enforced separately per-route via require_verified_email).
    SUSPENDED / DISABLED / DELETED block login outright with a distinct error
    so the client can render the right message instead of a generic 401.
    """

    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    DELETED = "deleted"


class RoleNameEnum(str, enum.Enum):
    """Built-in roles. Custom roles are stored as plain strings in Role.name."""

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    SALES = "sales"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationInvitationStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PermissionActionEnum(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    MANAGE = "manage"


# ─── CRM ─────────────────────────────────────────────────────────────────────


class LeadStatusEnum(str, enum.Enum):
    """
    Maps to the CRM pipeline stages. Values are ordered by sales progression.
    The pipeline is: new → contacted → interested → demo_scheduled →
    proposal → negotiation → won / lost / unqualified.
    """

    NEW = "new"
    RESEARCHING = "researching"  # AI is running research
    RESEARCH_DONE = "research_done"  # AI research complete, awaiting email gen
    EMAIL_GENERATED = "email_generated"  # AI generated email, awaiting approval
    CONTACTED = "contacted"  # First email sent
    OPENED = "opened"  # Email opened
    REPLIED = "replied"  # Prospect replied
    INTERESTED = "interested"  # Positive reply
    QUALIFIED = "qualified"  # Manually vetted as a real opportunity (CRM stage, distinct from the AI-outreach INTERESTED signal)
    DEMO_SCHEDULED = "demo_scheduled"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    UNQUALIFIED = "unqualified"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class ActivityTypeEnum(str, enum.Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    NOTE_ADDED = "note_added"
    NOTE_UPDATED = "note_updated"
    NOTE_DELETED = "note_deleted"
    STATUS_CHANGED = "status_changed"
    LEAD_IMPORTED = "lead_imported"
    AI_RESEARCH_STARTED = "ai_research_started"
    AI_RESEARCH_COMPLETED = "ai_research_completed"
    AI_EMAIL_GENERATED = "ai_email_generated"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    CALL_LOGGED = "call_logged"
    # Lead Management module (CRM > Leads)
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_DELETED = "lead_deleted"
    OWNER_CHANGED = "owner_changed"
    TAGS_CHANGED = "tags_changed"
    ATTACHMENT_UPLOADED = "attachment_uploaded"
    ATTACHMENT_DELETED = "attachment_deleted"
    LEAD_FAVORITED = "lead_favorited"
    LEAD_UNFAVORITED = "lead_unfavorited"
    LEAD_ARCHIVED = "lead_archived"
    LEAD_RESTORED = "lead_restored"
    BULK_ACTION = "bulk_action"
    # Company module (CRM > Companies)
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    COMPANY_ARCHIVED = "company_archived"
    COMPANY_RESTORED = "company_restored"
    COMPANY_DELETED = "company_deleted"
    LEAD_LINKED = "lead_linked"
    CONTACT_LINKED = "contact_linked"


class CompanySizeEnum(str, enum.Enum):
    SOLO = "1"
    MICRO = "2-10"
    SMALL = "11-50"
    MEDIUM = "51-200"
    LARGE = "201-1000"
    ENTERPRISE = "1001-5000"
    CORPORATION = "5000+"


class CompanyStatusEnum(str, enum.Enum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    CUSTOMER = "customer"
    PARTNER = "partner"
    CHURNED = "churned"
    INACTIVE = "inactive"


# ─── Campaigns ───────────────────────────────────────────────────────────────


class CampaignStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SequenceStepTypeEnum(str, enum.Enum):
    EMAIL = "email"
    LINKEDIN_MESSAGE = "linkedin_message"
    LINKEDIN_CONNECTION = "linkedin_connection"
    WAIT = "wait"
    TASK = "task"
    WEBHOOK = "webhook"


class EmailToneEnum(str, enum.Enum):
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    CASUAL = "casual"


class EmailTemplateTypeEnum(str, enum.Enum):
    COLD_OUTREACH = "cold_outreach"
    FOLLOW_UP = "follow_up"
    BREAK_UP = "break_up"
    LINKEDIN = "linkedin"
    MEETING_REQUEST = "meeting_request"
    PROPOSAL = "proposal"
    CUSTOM = "custom"


class CampaignLeadStatusEnum(str, enum.Enum):
    """Status of a lead *within* a specific campaign (not global lead status)."""

    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    REPLIED = "replied"
    MEETING_BOOKED = "meeting_booked"
    COMPLETED = "completed"
    OPTED_OUT = "opted_out"
    BOUNCED = "bounced"
    PAUSED = "paused"


# ─── Communication ───────────────────────────────────────────────────────────


class EmailStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    SPAM = "spam"


class EmailEventTypeEnum(str, enum.Enum):
    """
    Email events are append-only. We never update a single status field;
    instead we insert a new event row for each state transition.
    This gives us a complete delivery timeline per email.
    """

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"  # Marked as spam by recipient
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class ReplyClassificationEnum(str, enum.Enum):
    """AI-classified reply intent."""

    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    MEETING_REQUESTED = "meeting_requested"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    REFERRAL = "referral"
    OUT_OF_OFFICE = "out_of_office"
    SPAM = "spam"
    UNSUBSCRIBE_REQUEST = "unsubscribe_request"
    UNKNOWN = "unknown"


class MeetingStatusEnum(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


# ─── AI ──────────────────────────────────────────────────────────────────────


class AIAgentTypeEnum(str, enum.Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    PROSPECT_ANALYSIS = "prospect_analysis"
    EMAIL_GENERATION = "email_generation"
    REPLY_ANALYSIS = "reply_analysis"
    MEETING = "meeting"
    CRM = "crm"
    ANALYTICS = "analytics"


class AIJobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class LLMProviderEnum(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    GOOGLE = "google"
    MISTRAL = "mistral"
    LOCAL = "local"


# ─── Automation ──────────────────────────────────────────────────────────────


class WorkflowStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WorkflowExecutionStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledJobStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Billing ─────────────────────────────────────────────────────────────────


class PlanIntervalEnum(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatusEnum(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"


class InvoiceStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


# ─── Administration ──────────────────────────────────────────────────────────


class NotificationTypeEnum(str, enum.Enum):
    NEW_REPLY = "new_reply"
    MEETING_BOOKED = "meeting_booked"
    # Column is a plain String(50) (see Notification model), so this member
    # is migration-free — same pattern as IntegrationTypeEnum's later entries.
    MEETING_REMINDER = "meeting_reminder"
    EMAIL_FAILED = "email_failed"
    AI_RESEARCH_DONE = "ai_research_done"
    AI_EMAIL_GENERATED = "ai_email_generated"
    DAILY_SUMMARY = "daily_summary"
    LEAD_IMPORTED = "lead_imported"
    CAMPAIGN_COMPLETED = "campaign_completed"
    SYSTEM = "system"


class AuditActionEnum(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    EXPORT = "export"
    IMPORT = "import"
    REGISTER = "register"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    TOKEN_REFRESHED = "token_refreshed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFICATION_REQUESTED = "email_verification_requested"
    EMAIL_VERIFIED = "email_verified"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    SESSION_REVOKED = "session_revoked"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_SUSPENDED = "account_suspended"
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REVOKED = "invitation_revoked"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    BILLING_CHANGE = "billing_change"


class IntegrationTypeEnum(str, enum.Enum):
    GOOGLE_CALENDAR = "google_calendar"
    OUTLOOK_CALENDAR = "outlook_calendar"
    GMAIL = "gmail"
    OUTLOOK_EMAIL = "outlook_email"
    SMTP = "smtp"
    SLACK = "slack"
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    ZAPIER = "zapier"
    WEBHOOK = "webhook"
    LINKEDIN = "linkedin"
    STRIPE = "stripe"
    # AI provider credentials (org-level API keys, encrypted at rest on the
    # Integration row — see app/services/ai/ai_settings_service.py). The
    # column is a plain String(30), so adding members is migration-free.
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"
