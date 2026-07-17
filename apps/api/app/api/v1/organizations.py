import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import set_auth_cookies
from app.auth.dependencies import (
    ensure_same_organization,
    get_current_organization,
    require_permission,
)
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.exceptions.errors import NotFoundError, OrganizationNotFoundError
from app.models.identity.models import Organization, User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.auth import (
    AcceptInvitationRequest,
    InvitationResponse,
    InviteUserRequest,
    RoleResponse,
    UserResponse,
)
from app.schemas.common import ApiResponse
from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationMemberResponse,
    OrganizationUpdateRequest,
)
from app.schemas.serializers import (
    serialize_invitation,
    serialize_organization_detail,
    serialize_organization_member,
    serialize_role,
    serialize_user,
)
from app.security.device import build_device_info, get_client_ip
from app.services.invitation_service import InvitationService
from app.services.organization_service import OrganizationService
from app.services.session_service import SessionService

router = APIRouter(prefix="/organizations", tags=["organizations"])


async def _load_own_organization(
    organization_id: uuid.UUID, user: User, db: AsyncSession
) -> Organization:
    """
    Loads an organization by path-param id, scoped to the caller's own org.
    Under the current single-org-per-user model this is the only organization
    that can ever legitimately match — any other id (real or guessed) is
    reported as not-found rather than "forbidden", so this endpoint can't be
    used to enumerate which organization ids exist.
    """
    if organization_id != user.organization_id:
        raise OrganizationNotFoundError()
    organization = await OrganizationRepository(db).get_by_id(organization_id)
    if organization is None or organization.deleted_at is not None:
        raise OrganizationNotFoundError()
    return organization


async def _detail_response(organization: Organization, db: AsyncSession) -> OrganizationDetailResponse:
    member_count = await OrganizationRepository(db).count_members(organization.id)
    return serialize_organization_detail(organization, member_count=member_count)


# NOTE ON ROUTE ORDER: FastAPI matches routes in registration order, and
# `/{organization_id}` matches ANY single path segment — including literal
# strings like "roles" or "current". Every fixed-string route in this router
# (/current, /roles, /invitations, /invitations/accept) MUST be declared
# before the `/{organization_id}` family below it, or those requests would be
# misrouted into the id-based handlers instead (and fail UUID parsing).

# ─── Organization CRUD (list / current / create) ───────────────────────────────

@router.get("", response_model=ApiResponse[list[OrganizationDetailResponse]])
async def list_organizations(
    user: User = Depends(require_permission("organizations", "read")),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OrganizationDetailResponse]]:
    """
    Every user belongs to exactly one organization today (see
    `app/models/identity/models.py` — Organization docstring), so this always
    returns a single-item list: the caller's own organization. List-shaped for
    forward compatibility with multi-organization membership, a documented
    future capability, without being a breaking change when it lands.
    """
    return ApiResponse(data=[await _detail_response(organization, db)])


@router.post("", response_model=ApiResponse[None])
async def create_organization(
    payload: OrganizationCreateRequest,
    user: User = Depends(require_permission("organizations", "manage")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await OrganizationService(db).create_additional(actor=user, name=payload.name)


@router.get("/current", response_model=ApiResponse[OrganizationDetailResponse])
async def get_current_organization_route(
    user: User = Depends(require_permission("organizations", "read")),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    return ApiResponse(data=await _detail_response(organization, db))


@router.patch("/current", response_model=ApiResponse[OrganizationDetailResponse])
async def update_current_organization(
    payload: OrganizationUpdateRequest,
    user: User = Depends(require_permission("organizations", "update")),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    changes = payload.model_dump(exclude_unset=True)
    updated = await OrganizationService(db).update(organization, changes=changes, actor=user)
    return ApiResponse(data=await _detail_response(updated, db), message="Organization updated.")


# ─── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/roles", response_model=ApiResponse[list[RoleResponse]])
async def list_roles(
    user: User = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RoleResponse]]:
    """
    Lists the current organization's roles (id, name, description, is_system).
    Read-only — exists so clients can populate a role picker (e.g. the invite-
    member form) without guessing role UUIDs, which are generated per-org at
    creation time and are otherwise unknowable from the outside.
    """
    roles = await RoleRepository(db).list_for_organization(user.organization_id)
    return ApiResponse(data=[serialize_role(role) for role in roles])


# ─── Invitations ────────────────────────────────────────────────────────────────

@router.post(
    "/invitations",
    response_model=ApiResponse[InvitationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    payload: InviteUserRequest,
    user: User = Depends(require_permission("users", "create")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[InvitationResponse]:
    invitation, raw_token = await InvitationService(db).invite(
        organization_id=user.organization_id,
        email=payload.email,
        role_id=payload.role_id,
        invited_by=user.id,
    )
    meta = {"debug_invitation_token": raw_token} if settings.environment != "production" else None
    return ApiResponse(
        data=serialize_invitation(invitation), message="Invitation sent.", meta=meta
    )


@router.get("/invitations", response_model=ApiResponse[list[InvitationResponse]])
async def list_invitations(
    user: User = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[InvitationResponse]]:
    invitations = await InvitationService(db).list_pending(user.organization_id)
    return ApiResponse(data=[serialize_invitation(i) for i in invitations])


@router.delete("/invitations/{invitation_id}", response_model=ApiResponse[None])
async def revoke_invitation(
    invitation_id: uuid.UUID,
    user: User = Depends(require_permission("users", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    invitation = await InvitationRepository(db).get_by_id(invitation_id)
    if invitation is None:
        raise NotFoundError("Invitation not found.")
    ensure_same_organization(invitation.organization_id, user)
    await InvitationService(db).revoke(invitation, revoked_by=user.id)
    return ApiResponse(message="Invitation revoked.")


@router.post(
    "/invitations/accept",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    payload: AcceptInvitationRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserResponse]:
    user = await InvitationService(db).accept(
        payload.token,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password=payload.password,
    )
    ip_address = get_client_ip(request)
    access_token, refresh_token, _session = await SessionService(db).issue_token_pair(
        user,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        device_info=build_device_info(request.headers.get("user-agent")),
        remember_me=False,
    )
    await db.commit()
    set_auth_cookies(
        response, access_token=access_token, refresh_token=refresh_token, settings=settings
    )
    return ApiResponse(data=await serialize_user(user, db), message="Invitation accepted.")


# ─── Organization CRUD by id (must stay below every fixed-string route above) ──

@router.get("/{organization_id}", response_model=ApiResponse[OrganizationDetailResponse])
async def get_organization(
    organization_id: uuid.UUID,
    user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    organization = await _load_own_organization(organization_id, user, db)
    return ApiResponse(data=await _detail_response(organization, db))


@router.patch("/{organization_id}", response_model=ApiResponse[OrganizationDetailResponse])
async def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdateRequest,
    user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    organization = await _load_own_organization(organization_id, user, db)
    changes = payload.model_dump(exclude_unset=True)
    updated = await OrganizationService(db).update(organization, changes=changes, actor=user)
    return ApiResponse(data=await _detail_response(updated, db), message="Organization updated.")


@router.delete("/{organization_id}", response_model=ApiResponse[None])
async def delete_organization(
    organization_id: uuid.UUID,
    user: User = Depends(require_permission("organizations", "delete")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    organization = await _load_own_organization(organization_id, user, db)
    await OrganizationService(db).delete(organization, actor=user)
    return ApiResponse(message="Organization deleted.")


@router.post("/{organization_id}/logo", response_model=ApiResponse[OrganizationDetailResponse])
async def upload_organization_logo(
    organization_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    organization = await _load_own_organization(organization_id, user, db)
    updated = await OrganizationService(db).upload_logo(organization, file=file, actor=user)
    return ApiResponse(data=await _detail_response(updated, db), message="Logo updated.")


@router.delete("/{organization_id}/logo", response_model=ApiResponse[OrganizationDetailResponse])
async def delete_organization_logo(
    organization_id: uuid.UUID,
    user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationDetailResponse]:
    organization = await _load_own_organization(organization_id, user, db)
    updated = await OrganizationService(db).delete_logo(organization, actor=user)
    return ApiResponse(data=await _detail_response(updated, db), message="Logo removed.")


@router.get("/{organization_id}/members", response_model=ApiResponse[list[OrganizationMemberResponse]])
async def list_organization_members(
    organization_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    role: str | None = Query(default=None),
    sort_by: Literal["name", "email", "status", "joined_at", "last_active_at"] = Query(default="joined_at"),
    sort_desc: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OrganizationMemberResponse]]:
    organization = await _load_own_organization(organization_id, user, db)
    members, total = await OrganizationService(db).list_members(
        organization.id,
        search=search,
        status=status_filter,
        role_name=role,
        sort_by=sort_by,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=[serialize_organization_member(m) for m in members],
        meta={"page": page, "page_size": page_size, "total": total},
    )
