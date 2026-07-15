"""Shared httpOnly cookie helpers for any route that issues or clears a session."""

from fastapi import Request, Response

from app.core.config import Settings, get_settings
from app.exceptions.errors import AuthenticationError
from app.security.csrf import issue_csrf_cookie


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, settings: Settings
) -> None:
    response.set_cookie(
        settings.access_token_cookie_name,
        access_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        settings.refresh_token_cookie_name,
        refresh_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.jwt_refresh_token_remember_me_expire_days * 86400,
        path=f"{settings.api_v1_prefix}/auth",
    )
    issue_csrf_cookie(response)


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.access_token_cookie_name, path="/")
    response.delete_cookie(settings.refresh_token_cookie_name, path=f"{settings.api_v1_prefix}/auth")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def extract_refresh_token(request: Request, body_token: str | None) -> str:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_token_cookie_name) or body_token
    if not token:
        raise AuthenticationError("No refresh token provided.")
    return token
