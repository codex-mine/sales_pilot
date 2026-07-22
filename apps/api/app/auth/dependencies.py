"""
Reusable FastAPI dependencies for authentication, tenancy resolution, and
authorization. Every protected route in the application (this module and, in
future, CRM/campaigns/AI/billing routes) composes these instead of
re-implementing token parsing or role checks.

Design notes:
- `get_current_user` (and everything built on it) always re-derives identity
  from the database on every request — the access token only tells us *which*
  session and user to look up, never grants anything by itself. This is what
  "never trust frontend claims" means in practice: the JWT payload is a
  pointer, not a credential of truth.
- `require_permission` / `require_role` are dependency *factories* — call them
  with arguments at route-declaration time (`Depends(require_permission("leads", "read"))`),
  not the bare function, so no permission or role string is ever hardcoded
  inside a route body.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.exceptions.errors import (
    AccountSuspendedError,
    AuthenticationError,
    EmailNotVerifiedError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    SessionExpiredError,
)
from app.models.enums import RoleNameEnum, UserStatusEnum
from app.models.identity.models import Organization, Session, User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.security.permissions import role_priority
from app.security.tokens import decode_token
from app.services.rbac_service import RBACService

_LOGIN_BLOCKED_STATUSES = {
    UserStatusEnum.SUSPENDED,
    UserStatusEnum.DISABLED,
    UserStatusEnum.DELETED,
    UserStatusEnum.INACTIVE,
}


def _is_expired(dt) -> bool:
    from datetime import datetime, timezone

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= datetime.now(timezone.utc)


def _extract_access_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    return request.cookies.get(get_settings().access_token_cookie_name)


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: Session
    claims: dict


async def resolve_auth_context_from_token(token: str, db: AsyncSession) -> AuthContext:
    """The `Request`-independent half of `get_auth_context`: decode -> load
    session -> load user -> status check. Factored out so the WebSocket
    endpoint (`app/api/v1/ws_ai_jobs.py`) can authenticate a token pulled off
    `WebSocket.cookies`/`.query_params` through the exact same chain the HTTP
    dependency uses, instead of re-implementing session/user resolution."""
    payload = decode_token(token, expected_type="access")

    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(uuid.UUID(payload["session_id"]))
    if session is None or not session.is_active:
        raise SessionExpiredError()
    if _is_expired(session.expires_at):
        await session_repo.revoke(session)
        raise SessionExpiredError()

    user = await UserRepository(db).get_by_id(uuid.UUID(payload["sub"]))
    if user is None:
        raise AuthenticationError("User not found.")
    if user.status in _LOGIN_BLOCKED_STATUSES:
        raise AccountSuspendedError()

    return AuthContext(user=user, session=session, claims=payload)


async def get_auth_context(
    request: Request, db: AsyncSession = Depends(get_db)
) -> AuthContext:
    token = _extract_access_token(request)
    if token is None:
        raise AuthenticationError("Not authenticated.")
    return await resolve_auth_context_from_token(token, db)


async def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


async def get_current_session(ctx: AuthContext = Depends(get_auth_context)) -> Session:
    return ctx.session


async def get_current_organization(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Organization:
    organization = await OrganizationRepository(db).get_by_id(user.organization_id)
    if organization is None or not organization.is_active:
        raise OrganizationNotFoundError()
    return organization


async def get_current_workspace(
    organization: Organization = Depends(get_current_organization),
) -> Organization:
    """
    Alias for `get_current_organization`. In this schema "workspace" and
    "organization" are the same tenant boundary (see ARCHITECTURE.md — Team is
    a sub-unit, not a billing/RBAC boundary). Kept as a distinct dependency so
    route signatures read in workspace terms and can diverge without touching
    every call site if a separate Workspace concept is introduced later.
    """
    return organization


def require_verified_email(user: User = Depends(get_current_user)) -> User:
    if not user.email_verified:
        raise EmailNotVerifiedError()
    return user


def require_active_user(user: User = Depends(get_current_user)) -> User:
    if user.status != UserStatusEnum.ACTIVE:
        raise AccountSuspendedError("This action requires a fully activated account.")
    return user


def require_permission(resource: str, action: str):
    """Depends(require_permission("leads", "read")) — resolves against the DB, always."""

    async def dependency(
        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        allowed = await RBACService(db).has_permission(
            user.id, user.organization_id, resource, action
        )
        if not allowed:
            raise PermissionDeniedError(f"Missing permission: {resource}.{action}")
        return user

    return dependency


def require_role(role_name: str, *, at_least: bool = False):
    """
    Depends(require_role("admin")) requires exactly that role.
    Depends(require_role("admin", at_least=True)) requires that role or a
    higher-privileged one (see ROLE_PRIORITY in app/security/permissions.py).
    """

    async def dependency(
        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        roles = await RBACService(db).get_roles_for_user(user.id, user.organization_id)
        if not roles:
            raise PermissionDeniedError("You do not have a role in this organization.")
        if at_least:
            best_priority = min(role_priority(r.name) for r in roles)
            if best_priority > role_priority(role_name):
                raise PermissionDeniedError(f"Requires role '{role_name}' or higher.")
        elif not any(r.name == role_name for r in roles):
            raise PermissionDeniedError(f"Requires role '{role_name}'.")
        return user

    return dependency


require_organization_owner = require_role(RoleNameEnum.OWNER.value)
require_admin = require_role(RoleNameEnum.ADMIN.value, at_least=True)


def ensure_same_organization(resource_organization_id: uuid.UUID, user: User) -> None:
    """
    Tenant-isolation primitive for future domain routes (CRM, campaigns, AI, ...):
    call this after loading any organization-scoped row to guarantee the
    authenticated user's org matches the row's org, closing the "IDOR across
    tenants" gap that a bare `get_current_user` check does not.
    """
    if resource_organization_id != user.organization_id:
        raise OrganizationNotFoundError()
