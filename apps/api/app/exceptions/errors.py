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


class ValidationError(AppError):
    """For request-shape-valid-but-business-rule-invalid input (e.g. a bad
    file upload) that FastAPI/Pydantic's own 422 handling doesn't cover."""

    status_code = 400
    error_code = "validation_error"
    default_message = "The submitted data is invalid."


# ─── Rate limiting ─────────────────────────────────────────────────────────────

class RateLimitExceededError(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    default_message = "Too many requests. Please try again later."


# ─── AI / LLM providers ────────────────────────────────────────────────────────

class LLMProviderError(AppError):
    """Uniform wrapper for every provider-SDK failure (rate limits, auth,
    timeouts, malformed responses). Raised only by `app.services.ai.llm_client`
    so the AIJob failure path never has to branch on provider-specific
    exception types."""

    status_code = 502
    error_code = "llm_provider_error"
    default_message = "The AI provider request failed."


class AIOutputParsingError(AppError):
    """Raised by `AIJobService.execute_job` when a job requests
    `response_format="json"` and the model's output isn't valid JSON. Folded
    into the same FAILED path as `LLMProviderError` so malformed structured
    output never gets silently stored as if it were a successful result."""

    status_code = 502
    error_code = "ai_output_parsing_error"
    default_message = "The AI provider returned output that could not be parsed."


# ─── Email sending ─────────────────────────────────────────────────────────────

class EmailSendError(AppError):
    """Uniform wrapper for every sender-provider failure, mirroring
    `LLMProviderError`'s role for LLM providers — raised only by
    `app.services.email.sender_client` so the Email retry/failure path never
    branches on provider-specific exception types."""

    status_code = 502
    error_code = "email_send_error"
    default_message = "The email could not be sent."


# ─── Calendar / meeting scheduling ─────────────────────────────────────────────

class CalendarProviderError(AppError):
    """Uniform wrapper for every calendar-provider-SDK failure, mirroring
    `LLMProviderError`/`EmailSendError`'s role — raised only by
    `app.services.calendar.calendar_client` so callers never branch on
    provider-specific exception types."""

    status_code = 502
    error_code = "calendar_provider_error"
    default_message = "The calendar request failed."


class CalendarNotConnectedError(AppError):
    """Raised when an action needs a connected calendar (proposing times,
    confirming a booking) but the meeting owner has no active Google Calendar
    Integration row — distinct from a generic provider failure so the
    frontend can prompt reconnection specifically."""

    status_code = 400
    error_code = "calendar_not_connected"
    default_message = "Connect a Google Calendar before proposing times for this meeting."


class SlotUnavailableError(AppError):
    """Raised when a chosen booking slot fails re-validation at confirm time
    (the owner's calendar changed between proposal and the prospect's pick) —
    distinct from a generic validation error so the public booking page can
    show 'pick another time' rather than a generic failure message."""

    status_code = 409
    error_code = "slot_unavailable"
    default_message = "This time slot is no longer available. Please choose another."


class RecipientSuppressedError(AppError):
    """Raised when a synchronous send attempt targets a suppressed
    recipient (unsubscribed, or a prior hard bounce to the same address in
    this organization). The Email row is still marked FAILED with this
    reason for outbox visibility — this exception exists so the triggering
    HTTP request gets a distinct, actionable error instead of a generic 500."""

    status_code = 400
    error_code = "recipient_suppressed"
    default_message = "This recipient has unsubscribed or previously bounced and cannot be emailed."
