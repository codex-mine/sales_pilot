import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies, extract_refresh_token, set_auth_cookies
from app.auth.dependencies import (
    get_current_organization,
    get_current_session,
    get_current_user,
    get_current_workspace,
)
from app.core.config import Settings, get_settings
from app.core.redis import get_redis
from app.database.session import get_db
from app.exceptions.errors import PermissionDeniedError
from app.models.identity.models import Organization, Session, User
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    OrganizationResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.serializers import (
    serialize_organization,
    serialize_session,
    serialize_user,
)
from app.security.device import build_device_info, get_client_ip
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService
from app.services.session_service import SessionService

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Routes ─────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserResponse]:
    auth_service = AuthService(db, redis)
    ip_address = get_client_ip(request)
    user, verification_token = await auth_service.register(
        payload, ip_address=ip_address, user_agent=request.headers.get("user-agent")
    )

    access_token, refresh_token, _session = (
        await auth_service.sessions.issue_token_pair(
            user,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            device_info=build_device_info(request.headers.get("user-agent")),
            remember_me=False,
        )
    )
    await db.commit()
    set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
        settings=settings,
    )

    meta = {"expires_in": settings.jwt_access_token_expire_minutes * 60}
    if settings.environment != "production":
        meta["debug_email_verification_token"] = verification_token
    return ApiResponse(
        data=await serialize_user(user, db),
        message="Account created. Please verify your email.",
        meta=meta,
    )


@router.post("/login", response_model=ApiResponse[UserResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserResponse]:
    auth_service = AuthService(db, redis)
    ip_address = get_client_ip(request)
    user = await auth_service.authenticate(
        payload, ip_address=ip_address, user_agent=request.headers.get("user-agent")
    )
    access_token, refresh_token, _session = (
        await auth_service.sessions.issue_token_pair(
            user,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            device_info=build_device_info(request.headers.get("user-agent")),
            remember_me=payload.remember_me,
        )
    )
    await db.commit()
    set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
        settings=settings,
    )
    return ApiResponse(
        data=await serialize_user(user, db),
        message="Authenticated.",
        meta={"expires_in": settings.jwt_access_token_expire_minutes * 60},
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[TokenResponse]:
    raw_refresh_token = extract_refresh_token(
        request, payload.refresh_token if payload else None
    )
    access_token, new_refresh_token, _session, _user = await SessionService(db).rotate(
        raw_refresh_token
    )
    await db.commit()
    set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=new_refresh_token,
        settings=settings,
    )
    return ApiResponse(
        data=TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Token refreshed.",
    )


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    response: Response,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    await SessionRepository(db).revoke(session)
    await db.commit()
    clear_auth_cookies(response, settings)
    return ApiResponse(message="Logged out.")


@router.post("/logout-all", response_model=ApiResponse[None])
async def logout_all(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    await SessionService(db).revoke_all_sessions(user.id)
    await db.commit()
    clear_auth_cookies(response, settings)
    return ApiResponse(message="Logged out of all devices.")


@router.get("/me", response_model=ApiResponse[MeResponse])
async def me(
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    workspace: Organization = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MeResponse]:
    permissions = sorted(
        await RBACService(db).get_permission_keys(user.id, user.organization_id)
    )
    return ApiResponse(
        data=MeResponse(
            user=await serialize_user(user, db),
            organization=serialize_organization(organization),
            workspace=serialize_organization(workspace),
            permissions=permissions,
        )
    )


@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[None]:
    await AuthService(db, redis).change_password(user, payload)
    return ApiResponse(message="Password changed.")


@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    # Always return the same message regardless of whether the email exists —
    # revealing that difference would let an attacker enumerate registered users.
    token = await AuthService(db, redis).request_password_reset(payload.email)
    meta = None
    if settings.environment != "production" and token:
        meta = {"debug_reset_token": token}
    return ApiResponse(
        message="If an account with that email exists, a password reset link has been sent.",
        meta=meta,
    )


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[None]:
    await AuthService(db, redis).reset_password(payload.token, payload.new_password)
    return ApiResponse(message="Password reset. Please log in again.")


@router.post("/verify-email", response_model=ApiResponse[UserResponse])
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[UserResponse]:
    user = await AuthService(db, redis).verify_email(payload.token)
    return ApiResponse(data=await serialize_user(user, db), message="Email verified.")


@router.post("/resend-verification", response_model=ApiResponse[None])
async def resend_verification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    if user.email_verified:
        return ApiResponse(message="Email is already verified.")
    token = await AuthService(db, redis).resend_verification(user)
    meta = (
        {"debug_email_verification_token": token}
        if settings.environment != "production"
        else None
    )
    return ApiResponse(message="Verification email sent.", meta=meta)


@router.get("/sessions", response_model=ApiResponse[list[SessionResponse]])
async def list_sessions(
    user: User = Depends(get_current_user),
    current_session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SessionResponse]]:
    sessions = await SessionRepository(db).list_active_for_user(user.id)
    return ApiResponse(
        data=[
            serialize_session(s, current_session_id=current_session.id)
            for s in sessions
        ]
    )


@router.delete("/sessions/{session_id}", response_model=ApiResponse[None])
async def revoke_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SessionRepository(db)
    session = await repo.get_by_id(session_id)
    if session is None or session.user_id != user.id:
        raise PermissionDeniedError("Session not found.")
    await repo.revoke(session)
    await db.commit()
    return ApiResponse(message="Session revoked.")
