import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import set_auth_cookies
from app.auth.dependencies import ensure_same_organization, require_permission
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.exceptions.errors import NotFoundError
from app.models.identity.models import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.auth import (
    AcceptInvitationRequest,
    InvitationResponse,
    InviteUserRequest,
    RoleResponse,
    UserResponse,
)
from app.schemas.common import ApiResponse
from app.schemas.serializers import serialize_invitation, serialize_role, serialize_user
from app.security.device import build_device_info, get_client_ip
from app.services.invitation_service import InvitationService
from app.services.session_service import SessionService

router = APIRouter(prefix="/organizations", tags=["organizations"])


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
