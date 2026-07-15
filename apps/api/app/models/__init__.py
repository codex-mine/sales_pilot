"""
Central model import file.

Alembic's env.py imports Base from here, which triggers all model imports and
registers every table in Base.metadata. If a model file is not imported here,
Alembic will not detect it and autogenerate will silently omit its tables.
"""

from app.models.base import Base, BaseModel  # noqa: F401

# Import in FK dependency order (identity first — everything else points at it).
from app.models.identity.models import (  # noqa: F401,E501
    Organization, Team, User, Role, Permission,
    UserRole, RolePermission, TeamMember,
    Session, RefreshToken, PasswordResetToken, EmailVerificationToken,
    OrganizationInvitation,
)
from app.models.crm.models import (  # noqa: F401
    Company, Contact, Lead, LeadScore, Tag, LeadTag, Note, Activity, Attachment,
)
from app.models.campaigns.models import (  # noqa: F401
    Campaign, Sequence, SequenceStep, EmailTemplate, CampaignLead,
)
from app.models.communication.models import (  # noqa: F401
    Email, EmailEvent, Conversation, Message, Meeting, CalendarEvent,
)
from app.models.ai.models import (  # noqa: F401
    AIAgent, AIJob, AIOutput, CompanyResearch, ProspectAnalysis,
    PromptTemplate, PromptVersion, AIMemory,
)
from app.models.remaining_domains import (  # noqa: F401
    Workflow, WorkflowExecution, ScheduledJob,
    Event, Metric, Report, DashboardWidget,
    Notification, APIKey, Integration, AuditLog,
    Plan, Subscription, Invoice, Payment, UsageRecord,
)

__all__ = ["Base", "BaseModel"]
