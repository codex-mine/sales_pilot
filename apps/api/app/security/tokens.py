"""
JWT + opaque token issuance and verification.

Two distinct token families are used deliberately:
- Access/refresh tokens are JWTs (stateless verification, carry claims, have a
  `jti` for logging/audit correlation).
- Password-reset / email-verification / invitation tokens are opaque random
  strings, not JWTs. They are single-use and short-lived by design, so there
  is nothing to gain from making them self-describing — a JWT would only give
  an attacker more to inspect. Only a SHA-256 hash of the opaque token is ever
  persisted, mirroring how the refresh token hash is stored.
"""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.exceptions.errors import AuthenticationError


@dataclass(frozen=True)
class AccessTokenClaims:
    """
    Everything the access token asserts about the caller at issuance time.

    None of this is trusted blindly by the server on protected routes beyond
    identifying *who* is calling (`sub`) and *which session* issued the token
    (`session_id`) — permission and role checks always re-query Role/Permission
    tables. The claims exist so the frontend can render org/role context and
    so `permissions_version` can be used as a cheap staleness hint (see
    `User.permissions_version`).
    """

    user_id: str
    organization_id: str
    workspace_id: str
    role_id: str | None
    role_name: str | None
    permissions_version: int
    session_id: str


def _new_jti() -> str:
    return uuid.uuid4().hex


def create_access_token(claims: AccessTokenClaims) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": claims.user_id,
        "organization_id": claims.organization_id,
        "workspace_id": claims.workspace_id,
        "role_id": claims.role_id,
        "role_name": claims.role_name,
        "permissions_version": claims.permissions_version,
        "session_id": claims.session_id,
        "type": "access",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "jti": _new_jti(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str, session_id: str, *, remember_me: bool = False
) -> tuple[str, str, datetime]:
    """Returns (raw_jwt, jti, expires_at). The raw JWT is hashed by the caller before storage."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    days = (
        settings.jwt_refresh_token_remember_me_expire_days
        if remember_me
        else settings.jwt_refresh_token_expire_days
    )
    expires_at = now + timedelta(days=days)
    jti = _new_jti()
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expires_at,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    """Raises AuthenticationError on any structural, signature, expiry, or type mismatch."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type.")
    return payload


def create_unsubscribe_token(lead_id: str, organization_id: str) -> str:
    """One-click unsubscribe links must keep working indefinitely (a
    recipient may click a months-old email), so unlike password-reset/
    email-verification tokens this is long-lived and self-describing rather
    than opaque+short-lived — a JWT is the right shape here, verified with
    the existing `decode_token(..., expected_type="unsubscribe")` (no new
    decode path, no new secret: reuses `jwt_secret_key` per the module's own
    "reuse jwt_secret_key or a dedicated field" allowance)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": lead_id,
        "organization_id": organization_id,
        "type": "unsubscribe",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(days=3650),
        "jti": _new_jti(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_booking_token(meeting_id: str, organization_id: str) -> str:
    """The public meeting-booking link's token — same shape and reasoning as
    `create_unsubscribe_token` (a long-lived, self-describing JWT rather than
    an opaque short-lived one, since a prospect may open the link days after
    it was sent): reuses `jwt_secret_key` and the same
    `decode_token(..., expected_type="booking")` verification path, no new
    secret or decode mechanism. Expires in 30 days — long enough for a
    prospect to act, short enough that a stale, unactioned proposal doesn't
    stay bookable indefinitely."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": meeting_id,
        "organization_id": organization_id,
        "type": "booking",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(days=30),
        "jti": _new_jti(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def sign_click_url(tracking_pixel_id: str, url: str) -> str:
    """Signs a click-tracking redirect target so `/track/click/{id}` can't be
    used as an open redirector for arbitrary attacker-supplied URLs — reuses
    `jwt_secret_key`, the same signing key `create_unsubscribe_token` uses,
    but as a short HMAC digest rather than a JWT: a single email can contain
    many links, and a full JWT per link would bloat every href noticeably."""
    message = f"{tracking_pixel_id}:{url}".encode()
    return hmac.new(get_settings().jwt_secret_key.encode(), message, hashlib.sha256).hexdigest()


def verify_click_signature(tracking_pixel_id: str, url: str, signature: str) -> bool:
    expected = sign_click_url(tracking_pixel_id, url)
    return hmac.compare_digest(expected, signature)


def create_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
