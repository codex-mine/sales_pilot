"""
Custom exception hierarchy for the auth/RBAC layer.

Routes and services raise these instead of `HTTPException` directly so that:
- every error carries a stable machine-readable `error_code` the frontend can
  branch on (instead of parsing human-readable `message` strings), and
- the response body always matches the project-wide `ApiResponse` envelope.

`app.exceptions.handlers.register_exception_handlers` converts every subclass
below into that envelope. Add new failure modes here, not as ad-hoc
`HTTPException(...)` calls scattered across routes.
"""

from typing import Any


class AppError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = 400
    error_code: str = "app_error"
    default_message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        errors: dict[str, list[str]] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.errors = errors
        self.meta = meta
        super().__init__(self.message)


# ─── Authentication (who are you?) ────────────────────────────────────────────

class AuthenticationError(AppError):
    status_code = 401
    error_code = "authentication_error"
    default_message = "Not authenticated."


class InvalidCredentialsError(AuthenticationError):
    error_code = "invalid_credentials"
    default_message = "Invalid email or password."


class SessionExpiredError(AuthenticationError):
    error_code = "session_expired"
    default_message = "Your session has expired. Please log in again."


class TokenRevokedError(AuthenticationError):
    error_code = "token_revoked"
    default_message = "This token has been revoked."


class EmailNotVerifiedError(AuthenticationError):
    status_code = 403
    error_code = "email_not_verified"
    default_message = "Please verify your email address to continue."


class AccountSuspendedError(AuthenticationError):
    status_code = 403
    error_code = "account_suspended"
    default_message = "This account has been suspended."


class AccountLockedError(AuthenticationError):
    status_code = 423
    error_code = "account_locked"
    default_message = "This account is temporarily locked due to too many failed login attempts."


# ─── Authorization (are you allowed?) ─────────────────────────────────────────

class AuthorizationError(AppError):
    status_code = 403
    error_code = "authorization_error"
    default_message = "You do not have access to this resource."


class PermissionDeniedError(AuthorizationError):
    error_code = "permission_denied"
    default_message = "You do not have permission to perform this action."


# ─── Not found / conflict ─────────────────────────────────────────────────────

class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "The requested resource was not found."


class OrganizationNotFoundError(NotFoundError):
    error_code = "organization_not_found"
    default_message = "Organization not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "This resource already exists."


# ─── Rate limiting ─────────────────────────────────────────────────────────────

class RateLimitExceededError(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    default_message = "Too many requests. Please try again later."
