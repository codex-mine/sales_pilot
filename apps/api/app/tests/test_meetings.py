"""
Communication -> Meeting Scheduling & Calendar Booking tests: Google Calendar
OAuth connect/callback (encrypted token storage, CSRF state verification),
the GoogleCalendarClient's error-translation behavior (never a generic
failure), slot-planning arithmetic (busy-block exclusion, business hours),
the full create -> propose -> public-booking -> confirm lifecycle, re-
validation at confirm time, atomicity of confirm (a provider failure never
leaves a CONFIRMED Meeting without a CalendarEvent), reschedule/cancel
syncing to the external calendar, DEMO_SCHEDULED only firing on confirmation,
and permissions/multi-tenancy/token-strictness on every route.

The Google Calendar API itself is always stubbed — this suite never makes a
real network call to Google.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import CalendarProviderError
from app.models.identity.models import Role
from app.models.remaining_domains import Integration
from app.repositories.integration_repository import IntegrationRepository
from app.security.crypto import decrypt_secret, encrypt_secret
from app.services.calendar.calendar_client import ExternalEventResult
from app.services.calendar.google_oauth import GoogleTokenSet
from app.services.calendar.slot_planner import BusyBlock, generate_candidate_slots, is_slot_busy
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio

_INTEGRATION_TYPE = "google_calendar"


class _StubCalendarClient:
    """Swapped in for `get_calendar_client` inside `meeting_service.py` —
    never touches the real Google API."""

    def __init__(self) -> None:
        self.busy_blocks: list[BusyBlock] = []
        self.fail_create = False
        self.create_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    async def get_freebusy(self, integration, start, end):  # noqa: ANN001
        return self.busy_blocks

    async def create_event(self, integration, *, title, description, start, end, attendee_emails):  # noqa: ANN001
        self.create_calls.append({"start": start, "end": end, "attendees": attendee_emails})
        if self.fail_create:
            raise CalendarProviderError("Simulated Google Calendar outage.")
        return ExternalEventResult(
            provider_event_id=f"evt-{uuid.uuid4().hex}", provider_calendar_id="primary",
            meet_link="https://meet.google.com/abc-defg-hij", html_link="https://calendar.google.com/event",
        )

    async def update_event(self, integration, *, provider_event_id, start, end):  # noqa: ANN001
        self.update_calls.append({"provider_event_id": provider_event_id, "start": start, "end": end})
        return ExternalEventResult(
            provider_event_id=provider_event_id, provider_calendar_id="primary",
            meet_link="https://meet.google.com/abc-defg-hij", html_link=None,
        )

    async def delete_event(self, integration, *, provider_event_id):  # noqa: ANN001
        self.delete_calls.append({"provider_event_id": provider_event_id})


@pytest.fixture
def stub_calendar_client(monkeypatch) -> _StubCalendarClient:
    stub = _StubCalendarClient()
    monkeypatch.setattr(
        "app.services.communication.meeting_service.get_calendar_client", lambda provider, db: stub
    )
    return stub


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


def _user_id(registration: dict) -> str:
    return registration["data"]["id"]


async def _create_lead(client: AsyncClient, **overrides) -> dict:
    payload = {
        "first_name": "Grace", "last_name": "Hopper", "email": unique_email("lead"),
        "job_title": "VP Engineering", "company_name": "Acme Corp", **overrides,
    }
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _connect_calendar(db: AsyncSession, *, organization_id: str, user_id: str) -> Integration:
    integration = await IntegrationRepository(db).create(
        organization_id=uuid.UUID(organization_id), created_by=uuid.UUID(user_id), user_id=uuid.UUID(user_id),
        integration_type=_INTEGRATION_TYPE, name="rep@example.com",
        access_token_encrypted=encrypt_secret("stub-access-token"),
        refresh_token_encrypted=encrypt_secret("stub-refresh-token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar.events"],
        external_account_email="rep@example.com", external_account_id="rep@example.com", is_active=True,
    )
    await db.commit()
    return integration


async def _create_and_propose(
    client: AsyncClient, db: AsyncSession, *, organization_id: str, user_id: str, stub: _StubCalendarClient
) -> tuple[dict, dict, str]:
    """Full setup: connected calendar -> lead -> meeting -> proposed times.
    Returns (lead, meeting, booking_url)."""
    await _connect_calendar(db, organization_id=organization_id, user_id=user_id)
    lead = await _create_lead(client)
    created = await client.post(
        f"/api/v1/leads/{lead['id']}/meetings",
        json={"title": "Intro call", "duration_minutes": 30, "owner_id": user_id},
    )
    assert created.status_code == 201, created.text
    meeting = created.json()["data"]

    proposed = await client.post(f"/api/v1/meetings/{meeting['id']}/propose-times", json={"slot_count": 5})
    assert proposed.status_code == 200, proposed.text
    body = proposed.json()["data"]
    return lead, body["meeting"], body["booking_url"]


def _extract_booking_token(booking_url: str) -> str:
    return booking_url.rstrip("/").rsplit("/book/", 1)[-1]


async def _invite_and_accept(client: AsyncClient, db: AsyncSession, *, organization_id: str, role_name: str) -> AsyncClient:
    role = await db.scalar(
        select(Role).where(Role.organization_id == uuid.UUID(organization_id), Role.name == role_name)
    )
    assert role is not None
    invite = await client.post(
        "/api/v1/organizations/invitations", json={"email": unique_email(role_name), "role_id": str(role.id)}
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["meta"]["debug_invitation_token"]
    member_client = AsyncClient(transport=client._transport, base_url="http://test")
    accepted = await member_client.post(
        "/api/v1/organizations/invitations/accept",
        json={"token": token, "first_name": "New", "last_name": role_name.title(), "password": "Str0ng!Passw0rd"},
    )
    assert accepted.status_code == 201, accepted.text
    return member_client


# ─── Slot planner (pure logic, no mocking needed) ────────────────────────────────


def test_generate_candidate_slots_excludes_busy_blocks():
    now = datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)  # a Monday
    busy = [BusyBlock(start=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc), end=datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc))]
    candidates = generate_candidate_slots(
        busy, now=now, duration_minutes=30, slot_count=3, window_days=5,
        business_start_hour=9, business_end_hour=17,
    )
    assert len(candidates) == 3
    for slot in candidates:
        assert not is_slot_busy(slot["start"], slot["end"], busy)
    assert candidates[0]["start"] == datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)


def test_generate_candidate_slots_skips_weekends():
    now = datetime(2026, 7, 24, 16, 45, tzinfo=timezone.utc)  # Friday, near end of business day
    candidates = generate_candidate_slots(
        [], now=now, duration_minutes=30, slot_count=1, window_days=5,
        business_start_hour=9, business_end_hour=17,
    )
    assert len(candidates) == 1
    assert candidates[0]["start"].weekday() == 0  # rolled over the weekend to Monday


def test_generate_candidate_slots_respects_business_hours():
    now = datetime(2026, 7, 20, 20, 0, tzinfo=timezone.utc)  # 8pm Monday, after hours
    candidates = generate_candidate_slots(
        [], now=now, duration_minutes=30, slot_count=1, window_days=5,
        business_start_hour=9, business_end_hour=17,
    )
    assert candidates[0]["start"] == datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc)  # next business day, 9am


# ─── Google Calendar OAuth connect/callback ──────────────────────────────────────


async def test_calendar_connect_redirects_when_configured(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    monkeypatch.setattr(get_settings(), "google_calendar_client_id", "test-client-id")
    monkeypatch.setattr(get_settings(), "google_calendar_client_secret", "test-client-secret")
    response = await client.get("/api/v1/integrations/google-calendar/connect", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "accounts.google.com" in response.headers["location"]
    assert "google_oauth_state" in response.cookies


async def test_calendar_connect_fails_clearly_when_not_configured(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    monkeypatch.setattr(get_settings(), "google_calendar_client_id", None)
    monkeypatch.setattr(get_settings(), "google_calendar_client_secret", None)
    response = await client.get("/api/v1/integrations/google-calendar/connect", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "calendar_error=not_configured" in response.headers["location"]


async def test_calendar_callback_stores_encrypted_tokens(client: AsyncClient, db: AsyncSession, monkeypatch) -> None:
    registration = await register_user(client)

    def _stub_exchange(code: str) -> GoogleTokenSet:
        assert code == "fake-code"
        return GoogleTokenSet(
            access_token="plaintext-access-token", refresh_token="plaintext-refresh-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["https://www.googleapis.com/auth/calendar.events"], account_email="rep@example.com",
        )

    monkeypatch.setattr("app.services.calendar.calendar_integration_service.exchange_code_for_tokens", _stub_exchange)
    client.cookies.set("google_oauth_state", "matching-state")

    response = await client.get(
        "/api/v1/integrations/google-calendar/callback", params={"code": "fake-code", "state": "matching-state"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    assert "calendar_connected=1" in response.headers["location"]

    status_response = await client.get("/api/v1/integrations/google-calendar")
    data = status_response.json()["data"]
    assert data["is_connected"] is True
    assert data["account_email"] == "rep@example.com"

    integration = await db.scalar(
        select(Integration).where(
            Integration.organization_id == uuid.UUID(_org_id(registration)), Integration.integration_type == _INTEGRATION_TYPE
        )
    )
    assert integration is not None
    assert integration.access_token_encrypted != "plaintext-access-token"  # never stored in the clear
    assert decrypt_secret(integration.access_token_encrypted) == "plaintext-access-token"
    assert decrypt_secret(integration.refresh_token_encrypted) == "plaintext-refresh-token"


async def test_calendar_callback_rejects_state_mismatch(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    monkeypatch.setattr(
        "app.services.calendar.calendar_integration_service.exchange_code_for_tokens",
        lambda code: pytest.fail("must not exchange a code when state verification fails"),
    )
    client.cookies.set("google_oauth_state", "correct-state")
    response = await client.get(
        "/api/v1/integrations/google-calendar/callback", params={"code": "fake-code", "state": "wrong-state"},
        follow_redirects=False,
    )
    assert "calendar_error=connection_failed" in response.headers["location"]
    status_response = await client.get("/api/v1/integrations/google-calendar")
    assert status_response.json()["data"]["is_connected"] is False


async def test_disconnect_calendar(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    await _connect_calendar(db, organization_id=_org_id(registration), user_id=_user_id(registration))

    response = await client.delete("/api/v1/integrations/google-calendar")
    assert response.status_code == 200, response.text
    status_response = await client.get("/api/v1/integrations/google-calendar")
    assert status_response.json()["data"]["is_connected"] is False


async def test_disconnect_calendar_not_connected_returns_404(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.delete("/api/v1/integrations/google-calendar")
    assert response.status_code == 404


# ─── GoogleCalendarClient error translation ─────────────────────────────────────


async def test_google_calendar_client_translates_refresh_failure_clearly(
    client: AsyncClient, db: AsyncSession
) -> None:
    from google.auth.exceptions import RefreshError

    from app.services.calendar.calendar_client import GoogleCalendarClient

    registration = await register_user(client)
    integration = await _connect_calendar(db, organization_id=_org_id(registration), user_id=_user_id(registration))

    def _boom(service):
        raise RefreshError("invalid_grant: token has been revoked")

    calendar_client = GoogleCalendarClient(db)
    with pytest.raises(CalendarProviderError, match="[Rr]econnect"):
        await calendar_client._execute(integration, _boom)


# ─── Create -> propose -> public booking -> confirm ─────────────────────────────


async def test_propose_times_requires_connected_calendar(client: AsyncClient, db: AsyncSession) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    created = await client.post(f"/api/v1/leads/{lead['id']}/meetings", json={"title": "Intro call"})
    assert created.status_code == 201
    meeting_id = created.json()["data"]["id"]

    response = await client.post(f"/api/v1/meetings/{meeting_id}/propose-times", json={"slot_count": 5})
    assert response.status_code == 400
    assert response.json()["errors"] is None or "calendar" in response.text.lower()


async def test_full_booking_lifecycle_confirms_and_advances_lead_status(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    lead, meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    assert meeting["status"] == "proposed"
    assert len(meeting["proposed_times"]) == 5

    lead_before = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_before["status"] != "demo_scheduled"  # never advances on propose, only on confirm

    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    assert public_view.status_code == 200, public_view.text
    slots = public_view.json()["data"]["proposed_times"]
    assert len(slots) == 5

    chosen = slots[0]
    confirm = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})
    assert confirm.status_code == 200, confirm.text
    confirmed_data = confirm.json()["data"]
    assert confirmed_data["meeting_url"] == "https://meet.google.com/abc-defg-hij"
    assert len(stub_calendar_client.create_calls) == 1

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "demo_scheduled"


async def test_confirm_rejects_slot_not_among_proposed(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, _meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    fake_start = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat()
    fake_end = (datetime.now(timezone.utc) + timedelta(days=100, minutes=30)).isoformat()

    response = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": fake_start, "end": fake_end})
    assert response.status_code == 409
    assert len(stub_calendar_client.create_calls) == 0


async def test_confirm_revalidates_freebusy_and_rejects_now_busy_slot(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, _meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]

    # The owner's calendar filled up between proposal and confirmation.
    stub_calendar_client.busy_blocks = [
        BusyBlock(
            start=datetime.fromisoformat(chosen["start"].replace("Z", "+00:00")) - timedelta(minutes=5),
            end=datetime.fromisoformat(chosen["end"].replace("Z", "+00:00")) + timedelta(minutes=5),
        )
    ]

    response = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})
    assert response.status_code == 409
    assert len(stub_calendar_client.create_calls) == 0


async def test_confirm_atomic_provider_failure_leaves_meeting_proposed(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    stub_calendar_client.fail_create = True
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]

    response = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})
    assert response.status_code == 502

    meetings = await client.get("/api/v1/meetings")
    row = next(m for m in meetings.json()["data"] if m["id"] == meeting["id"])
    assert row["status"] == "proposed"
    assert row["calendar_event"] is None


async def test_public_booking_invalid_token_returns_404_without_leaking(client: AsyncClient) -> None:
    response = await client.get("/api/v1/book/not-a-real-token")
    assert response.status_code == 404


async def test_confirmed_meeting_no_longer_open_for_booking(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, _meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]
    first = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})
    assert first.status_code == 200

    second = await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})
    assert second.status_code == 400


# ─── Reschedule / cancel / outcome ────────────────────────────────────────────────


async def test_reschedule_syncs_external_calendar(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]
    await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})

    new_start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    new_end = new_start + timedelta(minutes=30)
    response = await client.post(
        f"/api/v1/meetings/{meeting['id']}/reschedule",
        json={"new_start": new_start.isoformat(), "new_end": new_end.isoformat()},
    )
    assert response.status_code == 200, response.text
    assert len(stub_calendar_client.update_calls) == 1


async def test_cancel_syncs_external_calendar_deletion(
    client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient
) -> None:
    registration = await register_user(client)
    _lead, meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]
    await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})

    response = await client.post(f"/api/v1/meetings/{meeting['id']}/cancel", json={"reason": "Prospect went dark."})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "cancelled"
    assert len(stub_calendar_client.delete_calls) == 1


async def test_log_outcome_completed(client: AsyncClient, db: AsyncSession, stub_calendar_client: _StubCalendarClient) -> None:
    registration = await register_user(client)
    _lead, meeting, booking_url = await _create_and_propose(
        client, db, organization_id=_org_id(registration), user_id=_user_id(registration), stub=stub_calendar_client
    )
    booking_token = _extract_booking_token(booking_url)
    public_view = await client.get(f"/api/v1/book/{booking_token}")
    chosen = public_view.json()["data"]["proposed_times"][0]
    await client.post(f"/api/v1/book/{booking_token}/confirm", json={"start": chosen["start"], "end": chosen["end"]})

    response = await client.post(f"/api/v1/meetings/{meeting['id']}/outcome", json={"status": "completed", "notes": "Great fit."})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "completed"


async def test_log_outcome_before_confirmation_rejected(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    created = await client.post(f"/api/v1/leads/{lead['id']}/meetings", json={"title": "Intro call"})
    meeting_id = created.json()["data"]["id"]

    response = await client.post(f"/api/v1/meetings/{meeting_id}/outcome", json={"status": "completed"})
    assert response.status_code == 400


# ─── Permissions + multi-tenancy ──────────────────────────────────────────────────


async def test_multi_tenancy_isolation_on_meetings(client: AsyncClient, db: AsyncSession) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    created = await client.post(f"/api/v1/leads/{lead['id']}/meetings", json={"title": "Intro call"})
    meeting_id = created.json()["data"]["id"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    cross_tenant = await other_client.post(f"/api/v1/meetings/{meeting_id}/cancel", json={})
    assert cross_tenant.status_code == 404
    await other_client.aclose()


async def test_viewer_can_read_meetings_but_not_create(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    lead = await _create_lead(client)

    viewer_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="viewer")
    listing = await viewer_client.get("/api/v1/meetings")
    assert listing.status_code == 200

    forbidden = await viewer_client.post(f"/api/v1/leads/{lead['id']}/meetings", json={"title": "Intro call"})
    assert forbidden.status_code == 403
    await viewer_client.aclose()
