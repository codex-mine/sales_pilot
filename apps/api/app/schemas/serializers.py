"""ORM -> response-schema mapping shared across auth and organization routes."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity.models import Organization, OrganizationInvitation, Role, Session, User
from app.schemas.auth import (
    InvitationResponse,
    OrganizationResponse,
    RoleResponse,
    SessionResponse,
    UserResponse,
)
from app.schemas.organizations import (
    OrganizationAddress,
    OrganizationDetailResponse,
    OrganizationMemberResponse,
)
from app.security.permissions import role_priority
from app.services.rbac_service import RBACService


async def serialize_user(user: User, db: AsyncSession) -> UserResponse:
    roles = await RBACService(db).get_roles_for_user(user.id, user.organization_id)
    # The singular `role` field surfaces the highest-privilege role a user holds.
    primary_role = min(roles, key=lambda r: role_priority(r.name)) if roles else None
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email_verified=user.email_verified,
        status=user.status,
        organization_id=str(user.organization_id),
        role=primary_role.name if primary_role else None,
        roles=[r.name for r in roles],
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
    )


def serialize_organization(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        timezone=organization.timezone,
        is_active=organization.is_active,
    )


def serialize_session(session: Session, *, current_session_id: uuid.UUID) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        ip_address=session.ip_address,
        device=session.device_info,
        is_current=session.id == current_session_id,
        created_at=session.created_at,
        last_active_at=session.last_active_at,
        expires_at=session.expires_at,
    )


def serialize_invitation(invitation: OrganizationInvitation) -> InvitationResponse:
    return InvitationResponse(
        id=str(invitation.id),
        email=invitation.email,
        role_id=str(invitation.role_id),
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


def serialize_role(role: Role) -> RoleResponse:
    return RoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        is_system=role.is_system,
    )


def serialize_organization_detail(
    organization: Organization, *, member_count: int
) -> OrganizationDetailResponse:
    return OrganizationDetailResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        domain=organization.domain,
        logo_url=organization.logo_url,
        website=organization.website,
        email=organization.email,
        phone=organization.phone,
        industry=organization.industry,
        country=organization.country,
        company_size=organization.company_size,
        timezone=organization.timezone,
        language=organization.language,
        currency=organization.currency,
        brand_color=organization.brand_color,
        description=organization.description,
        address=OrganizationAddress(**organization.address) if organization.address else None,
        is_active=organization.is_active,
        member_count=member_count,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


def serialize_organization_member(user: User) -> OrganizationMemberResponse:
    # `user.roles` must already be eager-loaded (see
    # UserRepository.list_for_organization's selectinload) — this stays a
    # plain sync function so it can be mapped over a list without N+1 queries.
    primary_role = min(user.roles, key=lambda r: role_priority(r.name)) if user.roles else None
    return OrganizationMemberResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=primary_role.name if primary_role else None,
        status=user.status,
        email_verified=user.email_verified,
        joined_at=user.created_at,
        last_active_at=user.last_login_at,
    )
