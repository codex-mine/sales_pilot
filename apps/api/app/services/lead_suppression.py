"""
The single "suppress this lead" action. An explicit unsubscribe-link click
(Email Sending, module 07), a spam complaint webhook (Email Tracking,
module 08), and an AI-classified UNSUBSCRIBE_REQUEST reply (Inbox, module
09) all funnel through here, so the `Lead.status` transition + Activity +
AuditLog shape is defined exactly once — each caller only supplies which
suppression reason and which AuditLog event key applies, so the three stay
distinguishable in the audit trail despite sharing this one code path.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm.models import Lead
from app.models.enums import AuditActionEnum, LeadStatusEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.leads import LeadUpdateRequest
from app.services.lead_service import LeadService

_SUPPRESSED_STATUSES = {LeadStatusEnum.UNSUBSCRIBED.value, LeadStatusEnum.BOUNCED.value}


async def suppress_lead(
    db: AsyncSession,
    lead: Lead,
    *,
    status: LeadStatusEnum,
    audit_event: str,
    actor: User,
    extra_changes: dict | None = None,
) -> bool:
    """Returns False (no-op) if the lead is already suppressed — callers
    that also need their own event-specific AuditLog entry (e.g. "email
    bounced hard") should write that separately; this only records the
    lead-suppression consequence itself."""
    if lead.status in _SUPPRESSED_STATUSES:
        return False

    await LeadService(db).update(lead, payload=LeadUpdateRequest(status=status.value), actor=actor)
    await AuditLogRepository(db).record(
        organization_id=lead.organization_id, actor_id=None, actor_email=None,
        action=AuditActionEnum.UPDATE, resource_type="lead", resource_id=lead.id,
        changes={"event": audit_event, **(extra_changes or {})},
    )
    return True
