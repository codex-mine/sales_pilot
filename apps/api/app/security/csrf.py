"""
Double-submit-cookie CSRF architecture.

Only relevant to cookie-authenticated browser sessions — a caller presenting
an `Authorization: Bearer` header instead (mobile apps, the future public API,
server-to-server calls) is not subject to CSRF and is always exempt, since
browsers do not automatically attach that header to cross-site requests.

Enforcement is gated to `environment == "production"` so local development and
tooling (curl, the test suite, early frontend integration before the header
is wired up) aren't blocked while the frontend CSRF-header plumbing lands.
This is what "ready" means here: the mechanism is fully implemented and
flipped on by environment, not bolted on later.
"""

import hmac
import secrets

from fastapi import Request, Response

from app.core.config import get_settings
from app.exceptions.errors import AuthenticationError


def issue_csrf_cookie(response: Response) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        httponly=False,  # must be readable by frontend JS to echo back in the header
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return token


def verify_csrf(request: Request) -> None:
    settings = get_settings()
    if settings.environment != "production":
        return
    if request.headers.get("authorization"):
        return
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise AuthenticationError("CSRF validation failed.")
