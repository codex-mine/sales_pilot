import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.security.passwords import validate_password_strength


def _validate_password_field(value: str) -> str:
    violations = validate_password_strength(value)
    if violations:
        raise ValueError(" ".join(violations))
    return value


# ─── Requests ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    organization_name: str = Field(min_length=1, max_length=255)

    _validate_password = field_validator("password")(_validate_password_field)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class RefreshRequest(BaseModel):
    """Refresh token is normally read from the httpOnly cookie; this body field
    is a fallback for non-browser clients (mobile apps, server-to-server)."""
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    _validate_password = field_validator("new_password")(_validate_password_field)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)

    _validate_password = field_validator("new_password")(_validate_password_field)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=16)


class InviteUserRequest(BaseModel):
    email: EmailStr
    role_id: uuid.UUID


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=16)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    _validate_password = field_validator("password")(_validate_password_field)


# ─── Responses ─────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_system: bool


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    timezone: str
    is_active: bool


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    email_verified: bool
    status: str
    organization_id: str
    role: str | None
    roles: list[str]
    avatar_url: str | None
    last_login_at: datetime | None


class MeResponse(BaseModel):
    user: UserResponse
    organization: OrganizationResponse
    workspace: OrganizationResponse
    permissions: list[str]


class SessionResponse(BaseModel):
    id: str
    ip_address: str | None
    device: dict | None
    is_current: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime


class InvitationResponse(BaseModel):
    id: str
    email: EmailStr
    role_id: str
    status: str
    expires_at: datetime
    created_at: datetime
