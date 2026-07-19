"""
Google Calendar OAuth2 authorization-code flow. The ONLY module that
constructs a `google_auth_oauthlib` Flow or touches an id_token — the
connect/callback routes and `calendar_integration_service.py` call into this
rather than the OAuth library directly, mirroring `llm_client.py`'s
single-dispatch-point shape for provider SDKs.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.exceptions.errors import CalendarProviderError

# calendar.events + calendar.freebusy per the module spec; userinfo.email
# (+ openid, which Google implicitly requires alongside it) is additive —
# lets the connected-account email be shown on the settings page without a
# second API round-trip (decoded straight from the returned id_token).
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


@dataclass
class GoogleTokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: list[str]
    account_email: str | None


def _require_configured() -> None:
    settings = get_settings()
    if not settings.google_calendar_client_id or not settings.google_calendar_client_secret:
        raise CalendarProviderError(
            "Google Calendar is not configured on this server. Set GOOGLE_CALENDAR_CLIENT_ID/SECRET."
        )


def _client_config() -> dict:
    settings = get_settings()
    return {
        "web": {
            "client_id": settings.google_calendar_client_id,
            "client_secret": settings.google_calendar_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_calendar_redirect_uri],
        }
    }


def build_authorization_url(state: str) -> str:
    """`state` carries the connecting user's id (HMAC-signed by the caller)
    so the callback can attribute the exchanged tokens without trusting a
    caller-supplied user id in the query string."""
    _require_configured()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_CALENDAR_SCOPES, state=state)
    flow.redirect_uri = get_settings().google_calendar_redirect_uri
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # forces a refresh_token on every (re)connect, not just the first
    )
    return authorization_url


def exchange_code_for_tokens(code: str) -> GoogleTokenSet:
    _require_configured()
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import id_token as google_id_token
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(_client_config(), scopes=GOOGLE_CALENDAR_SCOPES)
    flow.redirect_uri = get_settings().google_calendar_redirect_uri
    try:
        flow.fetch_token(code=code)
    except Exception as exc:  # noqa: BLE001 — uniform provider-error boundary
        raise CalendarProviderError(f"Google Calendar authorization failed: {exc}") from exc

    creds = flow.credentials
    if not creds.token:
        raise CalendarProviderError("Google Calendar did not return an access token.")
    if not creds.refresh_token:
        # Google only issues a refresh_token when the user hasn't already
        # granted this app consent — `prompt="consent"` above prevents this
        # in the normal flow, but a stale approval can still slip through.
        raise CalendarProviderError(
            "Google did not grant offline access. Revoke SalesPilot's access at "
            "https://myaccount.google.com/permissions and reconnect."
        )

    account_email = None
    if creds.id_token:
        try:
            claims = google_id_token.verify_oauth2_token(
                creds.id_token, GoogleAuthRequest(), audience=get_settings().google_calendar_client_id
            )
            account_email = claims.get("email")
        except Exception:  # noqa: BLE001 — email is a display nicety, never fatal to connecting
            account_email = None

    expires_at = (
        creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return GoogleTokenSet(
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        expires_at=expires_at,
        scopes=list(creds.scopes or GOOGLE_CALENDAR_SCOPES),
        account_email=account_email,
    )
