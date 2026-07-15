from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService
router = APIRouter(prefix="/auth", tags=["auth"])
def serialize(user: User) -> UserResponse: return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, is_verified=user.is_verified)
def set_refresh_cookie(response: Response, token: str) -> None: response.set_cookie("refresh_token", token, httponly=True, secure=get_settings().secure_cookies, samesite="lax", max_age=get_settings().jwt_refresh_token_expire_days * 86400, path="/api/v1/auth")
@router.post("/register", response_model=ApiResponse[UserResponse], status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[UserResponse]: return ApiResponse(data=serialize(await AuthService(db).register(payload)), message="Account created")
@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    access, refresh = await AuthService(db).issue_tokens(await AuthService(db).authenticate(payload)); set_refresh_cookie(response, refresh); return ApiResponse(data=TokenResponse(access_token=access), message="Authenticated")
@router.post("/logout", response_model=ApiResponse[None])
async def logout(response: Response) -> ApiResponse[None]: response.delete_cookie("refresh_token", path="/api/v1/auth"); return ApiResponse(message="Logged out")
@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(user: User = Depends(get_current_user)) -> ApiResponse[UserResponse]: return ApiResponse(data=serialize(user))
# Forgot/reset/verify/change-password contracts are intentionally reserved for transactional-email integration in a later phase.
