"""
Google Calendar OAuth connect/callback + status/disconnect (Settings ->
Calendar Integration). A personal, user-level integration — every route here
depends only on `get_current_user`, no RBAC permission (see
`CalendarIntegrationService`'s own docstring: connecting your own calendar
isn't an organization-wide action).

`/connect` and `/callback` are the two legs of the standard OAuth2
authorization-code flow: `/connect` redirects to Google's consent screen
(setting a short-lived, httpOnly CSRF `state` cookie first); Google redirects
the browser back to `/callback` on the same origin, so the user's normal
session cookie is still attached — no need to smuggle identity through
`state`, which exists purely as the anti-CSRF nonce OAuth2 expects.
"""

import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_db
from app.exceptions.errors import CalendarProviderError
from app.models.identity.models import User
from app.schemas.common import ApiResponse
from app.schemas.meetings import CalendarConnectionStatusResponse
from app.services.calendar.calendar_integration_service import CalendarIntegrationService

router = APIRouter(prefix="/integrations/google-calendar", tags=["integrations"])

_STATE_COOKIE_NAME = "google_oauth_state"


def _state_cookie_path() -> str:
    return f"{get_settings().api_v1_prefix}/integrations/google-calendar"


@router.get("", response_model=ApiResponse[CalendarConnectionStatusResponse])
async def get_calendar_connection_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ApiResponse[CalendarConnectionStatusResponse]:
    status = await CalendarIntegrationService(db).status(user.organization_id, user)
    return ApiResponse(data=CalendarConnectionStatusResponse(**status))


@router.get("/connect")
async def connect_google_calendar(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    try:
        authorization_url = CalendarIntegrationService(db).build_connect_url(state)
    except CalendarProviderError:
        return RedirectResponse(url=f"{settings.frontend_url}/settings/calendar?calendar_error=not_configured")

    response = RedirectResponse(url=authorization_url)
    response.set_cookie(
        _STATE_COOKIE_NAME, state, httponly=True, secure=settings.secure_cookies,
        samesite="lax", max_age=600, path=_state_cookie_path(),
    )
    return response


@router.get("/callback")
async def google_calendar_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    redirect_base = f"{settings.frontend_url}/settings/calendar"
    stored_state = request.cookies.get(_STATE_COOKIE_NAME)
    state_ok = bool(state and stored_state and secrets.compare_digest(state, stored_state))

    if error or not code or not state_ok:
        response = RedirectResponse(url=f"{redirect_base}?calendar_error=connection_failed")
    else:
        try:
            await CalendarIntegrationService(db).handle_callback(
                organization_id=user.organization_id, user=user, code=code
            )
        except CalendarProviderError:
            response = RedirectResponse(url=f"{redirect_base}?calendar_error=connection_failed")
        else:
            response = RedirectResponse(url=f"{redirect_base}?calendar_connected=1")

    response.delete_cookie(_STATE_COOKIE_NAME, path=_state_cookie_path())
    return response


@router.delete("", response_model=ApiResponse[None])
async def disconnect_google_calendar(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ApiResponse[None]:
    await CalendarIntegrationService(db).disconnect(user.organization_id, user)
    return ApiResponse(message="Google Calendar disconnected.")
