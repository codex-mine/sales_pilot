"""
Provider-agnostic calendar client layer for already-connected calendars. This
module is the ONLY place in the codebase where a calendar provider SDK is
imported and where provider branching happens for ongoing operations
(freebusy/create/update/delete) — mirrors `app.services.ai.llm_client`'s and
`app.services.email.sender_client`'s single-dispatch-point shape exactly.
OAuth connect/callback itself lives in `google_oauth.py`, not here.

Every provider SDK exception is caught and re-raised as `CalendarProviderError`
so callers (meeting_service) never branch on provider-specific exceptions.
Google's access-token refresh happens transparently inside `googleapiclient`
(via `AuthorizedHttp`, which refreshes an expired token before the request
using the stored `refresh_token`) — this client's job is only to notice when
that happened and persist the new access token, and to translate a failed
refresh (revoked/expired refresh_token) into a clear "reconnect" error instead
of a generic failure.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import CalendarNotConnectedError, CalendarProviderError
from app.models.remaining_domains import Integration
from app.repositories.integration_repository import IntegrationRepository
from app.security.crypto import decrypt_secret, encrypt_secret
from app.services.calendar.google_oauth import GOOGLE_CALENDAR_SCOPES
from app.services.calendar.slot_planner import BusyBlock

# Personal "connect your own calendar" integrations only ever address the
# connecting account's primary calendar — Google Calendar API's "primary"
# alias resolves this without needing to look up/store a separate calendar id.
_PRIMARY_CALENDAR_ID = "primary"


@dataclass
class ExternalEventResult:
    provider_event_id: str
    provider_calendar_id: str
    meet_link: str | None
    html_link: str | None
    raw_response: dict = field(default_factory=dict)


class CalendarClient(ABC):
    @abstractmethod
    async def get_freebusy(self, integration: Integration, start: datetime, end: datetime) -> list[BusyBlock]: ...

    @abstractmethod
    async def create_event(
        self,
        integration: Integration,
        *,
        title: str,
        description: str | None,
        start: datetime,
        end: datetime,
        attendee_emails: list[str],
    ) -> ExternalEventResult: ...

    @abstractmethod
    async def update_event(
        self, integration: Integration, *, provider_event_id: str, start: datetime, end: datetime
    ) -> ExternalEventResult: ...

    @abstractmethod
    async def delete_event(self, integration: Integration, *, provider_event_id: str) -> None: ...


class GoogleCalendarClient(CalendarClient):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _build_credentials(self, integration: Integration):
        from google.oauth2.credentials import Credentials

        from app.core.config import get_settings

        access_token = decrypt_secret(integration.access_token_encrypted) if integration.access_token_encrypted else None
        refresh_token = decrypt_secret(integration.refresh_token_encrypted) if integration.refresh_token_encrypted else None
        if not access_token or not refresh_token:
            raise CalendarNotConnectedError()

        settings = get_settings()
        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_calendar_client_id,
            client_secret=settings.google_calendar_client_secret,
            scopes=integration.scopes or GOOGLE_CALENDAR_SCOPES,
        )

    async def _persist_refreshed_token(self, integration: Integration, creds: Any) -> None:
        expires_at = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
        await IntegrationRepository(self.db).update(
            integration,
            {"access_token_encrypted": encrypt_secret(creds.token), "token_expires_at": expires_at},
            updated_by=None,
        )
        await self.db.commit()

    async def _execute(
        self, integration: Integration, fn: Callable[[Any], Any], *, ignore_statuses: tuple[int, ...] = ()
    ) -> Any:
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError

        creds = self._build_credentials(integration)
        original_token = creds.token

        def _run() -> Any:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            return fn(service)

        result = None
        try:
            result = await asyncio.to_thread(_run)
        except RefreshError as exc:
            raise CalendarProviderError(
                "Google Calendar authorization has expired or was revoked. Reconnect your calendar."
            ) from exc
        except HttpError as exc:
            status = exc.resp.status if exc.resp else None
            if status not in ignore_statuses:
                raise CalendarProviderError(f"Google Calendar request failed: {exc}") from exc

        if creds.token and creds.token != original_token:
            await self._persist_refreshed_token(integration, creds)
        return result

    async def get_freebusy(self, integration: Integration, start: datetime, end: datetime) -> list[BusyBlock]:
        def _call(service: Any) -> dict:
            body = {
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": _PRIMARY_CALENDAR_ID}],
            }
            return service.freebusy().query(body=body).execute()

        response = await self._execute(integration, _call)
        busy_raw = (response or {}).get("calendars", {}).get(_PRIMARY_CALENDAR_ID, {}).get("busy", [])
        return [
            BusyBlock(start=datetime.fromisoformat(slot["start"]), end=datetime.fromisoformat(slot["end"]))
            for slot in busy_raw
        ]

    async def create_event(
        self,
        integration: Integration,
        *,
        title: str,
        description: str | None,
        start: datetime,
        end: datetime,
        attendee_emails: list[str],
    ) -> ExternalEventResult:
        def _call(service: Any) -> dict:
            body = {
                "summary": title,
                "description": description or "",
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
                "attendees": [{"email": email} for email in attendee_emails],
                "conferenceData": {
                    "createRequest": {
                        "requestId": uuid.uuid4().hex,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }
            return (
                service.events()
                .insert(calendarId=_PRIMARY_CALENDAR_ID, body=body, conferenceDataVersion=1, sendUpdates="all")
                .execute()
            )

        response = await self._execute(integration, _call)
        meet_link = None
        for entry_point in (response.get("conferenceData", {}).get("entryPoints") or []):
            if entry_point.get("entryPointType") == "video":
                meet_link = entry_point.get("uri")
                break
        return ExternalEventResult(
            provider_event_id=response["id"],
            provider_calendar_id=_PRIMARY_CALENDAR_ID,
            meet_link=meet_link,
            html_link=response.get("htmlLink"),
            raw_response=response,
        )

    async def update_event(
        self, integration: Integration, *, provider_event_id: str, start: datetime, end: datetime
    ) -> ExternalEventResult:
        def _call(service: Any) -> dict:
            body = {"start": {"dateTime": start.isoformat()}, "end": {"dateTime": end.isoformat()}}
            return (
                service.events()
                .patch(calendarId=_PRIMARY_CALENDAR_ID, eventId=provider_event_id, body=body, sendUpdates="all")
                .execute()
            )

        response = await self._execute(integration, _call)
        return ExternalEventResult(
            provider_event_id=response["id"],
            provider_calendar_id=_PRIMARY_CALENDAR_ID,
            meet_link=None,
            html_link=response.get("htmlLink"),
            raw_response=response,
        )

    async def delete_event(self, integration: Integration, *, provider_event_id: str) -> None:
        def _call(service: Any) -> None:
            service.events().delete(
                calendarId=_PRIMARY_CALENDAR_ID, eventId=provider_event_id, sendUpdates="all"
            ).execute()
            return None

        # 404/410 means the event is already gone on Google's side — treated
        # as a successful delete so a local cancel is never blocked by it.
        await self._execute(integration, _call, ignore_statuses=(404, 410))


def get_calendar_client(provider: str, db: AsyncSession) -> CalendarClient:
    """The single point of provider branching for ongoing calendar
    operations. Only "google_calendar" is implemented; the shape (an ABC +
    one factory) keeps Outlook additive later without touching call sites."""
    if provider == "google_calendar":
        return GoogleCalendarClient(db)
    raise CalendarProviderError(f"Unsupported calendar provider: '{provider}'.")
