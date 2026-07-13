from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_db
from app.models.entities import User
from app.schemas.auth import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, TokenResponse, UserResponse, VerifyEmailRequest
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

def serialize(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, is_verified=user.is_verified)

def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie("refresh_token", token, httponly=True, secure=settings.secure_cookies, samesite="lax", max_age=settings.jwt_refresh_token_expire_days * 86400, path="/api/v1/auth")

def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/api/v1/auth")

def development_meta(token: str | None, purpose: str) -> dict[str, object] | None:
    # This makes local email flows testable without an SMTP provider. It is impossible
    # to expose in staging/production, where an email adapter must deliver the token.
    return {"development_token": token, "purpose": purpose} if get_settings().environment == "development" and token else None

@router.post("/register", response_model=ApiResponse[UserResponse], status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[UserResponse]:
    user, verification = await AuthService(db).register(payload)
    return ApiResponse(data=serialize(user), message="Account created. Verify your email.", meta=development_meta(verification, "email_verification"))

@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    access, refresh = await AuthService(db).issue_tokens(await AuthService(db).authenticate(payload))
    set_refresh_cookie(response, refresh)
    return ApiResponse(data=TokenResponse(access_token=access), message="Authenticated")

@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    access, next_refresh = await AuthService(db).refresh(refresh_token or "")
    set_refresh_cookie(response, next_refresh)
    return ApiResponse(data=TokenResponse(access_token=access), message="Token refreshed")

@router.post("/logout", response_model=ApiResponse[None])
async def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> ApiResponse[None]:
    await AuthService(db).revoke(refresh_token)
    clear_refresh_cookie(response)
    return ApiResponse(message="Logged out")

@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[None]:
    token = await AuthService(db).request_password_reset(str(payload.email))
    return ApiResponse(message="If an account exists, reset instructions have been issued.", meta=development_meta(token, "password_reset"))

@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[None]:
    await AuthService(db).reset_password(payload.token, payload.password)
    return ApiResponse(message="Password reset")

@router.post("/verify-email", response_model=ApiResponse[None])
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[None]:
    await AuthService(db).verify_email(payload.token)
    return ApiResponse(message="Email verified")

@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ApiResponse[None]:
    await AuthService(db).change_password(user, payload.current_password, payload.new_password)
    return ApiResponse(message="Password changed; sign in again")

@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(user: User = Depends(get_current_user)) -> ApiResponse[UserResponse]:
    return ApiResponse(data=serialize(user))