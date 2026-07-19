"""
Resolves a real `User` to attribute automated/system-triggered actions to.

Several service-layer calls (`LeadService.update`, etc.) require a `User`
actor for their Activity/AuditLog summaries even when the trigger is a
public, unauthenticated event — an unsubscribe click, a delivery webhook, a
tracking pixel fire. Rather than widening those shared contracts to accept a
nullable actor for this handful of callers, this resolves the organization's
owner as the recording actor: mirrors how `AIJob.initiated_by` is nullable
for automated actions, but `LeadService`'s own contract always wants a real
`User`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.identity.models import Role, User, UserRole


async def resolve_org_owner(db: AsyncSession, organization_id: uuid.UUID) -> User:
    owner = await db.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.organization_id == organization_id, Role.name == "owner")
        .limit(1)
    )
    if owner is None:
        raise NotFoundError("Organization owner not found.")
    return owner
