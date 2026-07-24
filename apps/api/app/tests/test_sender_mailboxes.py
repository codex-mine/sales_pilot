"""
Phase X Issue 01 -> Sender Mailbox Management: a real SMTP connection test
runs before a mailbox is ever saved (failure -> not saved, exact error
returned), multiple mailboxes per org with a single default, set-default
correctly demotes the previous default, and a manually-chosen mailbox is
recorded on the Email row for audit (`personalization_data.sender_mailbox_id`)
and actually used to resolve send credentials.
"""

import smtplib
import socket
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


class _FakeSMTP:
    """Stands in for `smtplib.SMTP`/`smtplib.SMTP_SSL` as a context manager.
    `_behavior` picks which failure (if any) `login`/`noop` should raise."""

    def __init__(self, host, port, timeout=None, context=None, *, _behavior="ok"):
        if _BEHAVIOR["mode"] == "invalid_host":
            raise socket.gaierror("Name or service not known")
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, username, password):
        if _BEHAVIOR["mode"] == "auth_fail":
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")

    def noop(self):
        if _BEHAVIOR["mode"] == "noop_fail":
            raise smtplib.SMTPServerDisconnected("Connection closed")

    def send_message(self, message):
        # Patching `smtplib.SMTP` is process-global, so this stub also
        # stands in for the transactional auth-email sender
        # (`app/services/email_service.py`) during `register_user()` in
        # these tests — it never actually sends anything either way.
        pass


_BEHAVIOR = {"mode": "ok"}


@pytest.fixture(autouse=True)
def reset_behavior():
    _BEHAVIOR["mode"] = "ok"
    yield
    _BEHAVIOR["mode"] = "ok"


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch):
    monkeypatch.setattr("app.services.email.sender_client.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("app.services.email.sender_client.smtplib.SMTP_SSL", _FakeSMTP)


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


async def _create_mailbox(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": "Sales team", "email_address": "sales@example.com", "host": "smtp.example.com",
        "port": 587, "username": "sales@example.com", "password": "correct-horse", "encryption_type": "starttls",
        **overrides,
    }
    response = await client.post("/api/v1/settings/email-sender/mailboxes", json=payload)
    return response


async def test_create_mailbox_runs_connection_test_and_saves_on_success(client: AsyncClient) -> None:
    await register_user(client)
    response = await _create_mailbox(client)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["host"] == "smtp.example.com"
    assert data["email_address"] == "sales@example.com"
    assert data["is_default"] is True  # first mailbox for the org is always default
    assert "password" not in data


async def test_create_mailbox_rejects_and_does_not_save_on_auth_failure(client: AsyncClient) -> None:
    await register_user(client)
    _BEHAVIOR["mode"] = "auth_fail"

    response = await _create_mailbox(client)
    assert response.status_code == 400, response.text
    assert "authentication" in response.json()["message"].lower()

    listed = await client.get("/api/v1/settings/email-sender/mailboxes")
    assert listed.json()["data"] == []  # nothing was persisted


async def test_create_mailbox_rejects_invalid_host(client: AsyncClient) -> None:
    await register_user(client)
    _BEHAVIOR["mode"] = "invalid_host"
    response = await _create_mailbox(client, host="this-host-does-not-resolve.invalid.test")
    assert response.status_code == 400, response.text
    assert "invalid smtp host" in response.json()["message"].lower()
    _BEHAVIOR["mode"] = "ok"
    listed = await client.get("/api/v1/settings/email-sender/mailboxes")
    assert listed.json()["data"] == []


async def test_test_connection_endpoint_does_not_persist(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/settings/email-sender/mailboxes/test-connection",
        json={"host": "smtp.example.com", "port": 587, "username": "u", "password": "p", "encryption_type": "starttls"},
    )
    assert response.status_code == 200, response.text
    listed = await client.get("/api/v1/settings/email-sender/mailboxes")
    assert listed.json()["data"] == []


async def test_second_mailbox_is_not_default_until_explicitly_set(client: AsyncClient) -> None:
    await register_user(client)
    first = await _create_mailbox(client, name="First")
    second = await _create_mailbox(client, name="Second", email_address="second@example.com")
    assert first.json()["data"]["is_default"] is True
    assert second.json()["data"]["is_default"] is False

    set_default = await client.post(f"/api/v1/settings/email-sender/mailboxes/{second.json()['data']['id']}/set-default")
    assert set_default.status_code == 200, set_default.text
    assert set_default.json()["data"]["is_default"] is True

    refreshed_first = await client.get("/api/v1/settings/email-sender/mailboxes")
    by_id = {m["id"]: m for m in refreshed_first.json()["data"]}
    assert by_id[first.json()["data"]["id"]]["is_default"] is False
    assert by_id[second.json()["data"]["id"]]["is_default"] is True


async def test_update_mailbox_reverifies_on_credential_change(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_mailbox(client)
    mailbox_id = created.json()["data"]["id"]

    _BEHAVIOR["mode"] = "auth_fail"
    response = await client.patch(f"/api/v1/settings/email-sender/mailboxes/{mailbox_id}", json={"password": "new-wrong-pass"})
    assert response.status_code == 400, response.text

    # Non-credential field update (name only) must NOT trigger re-verification.
    _BEHAVIOR["mode"] = "auth_fail"
    renamed = await client.patch(f"/api/v1/settings/email-sender/mailboxes/{mailbox_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["data"]["name"] == "Renamed"


async def test_delete_mailbox(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_mailbox(client)
    mailbox_id = created.json()["data"]["id"]
    deleted = await client.delete(f"/api/v1/settings/email-sender/mailboxes/{mailbox_id}")
    assert deleted.status_code == 200, deleted.text
    listed = await client.get("/api/v1/settings/email-sender/mailboxes")
    assert listed.json()["data"] == []


async def test_mailboxes_scoped_to_organization(client: AsyncClient) -> None:
    await register_user(client)
    created = await _create_mailbox(client)
    mailbox_id = created.json()["data"]["id"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    other_listed = await other_client.get("/api/v1/settings/email-sender/mailboxes")
    assert other_listed.json()["data"] == []

    forbidden_update = await other_client.patch(f"/api/v1/settings/email-sender/mailboxes/{mailbox_id}", json={"name": "x"})
    assert forbidden_update.status_code == 404


async def test_manual_mailbox_selection_used_for_send_and_recorded_for_audit(
    client: AsyncClient, db: AsyncSession, monkeypatch
) -> None:
    """A specific `sender_mailbox_id` tagged on `Email.personalization_data`
    must be the mailbox `EmailSendingService` actually resolves credentials
    from — proving the audit trail is load-bearing, not just cosmetic."""
    from app.models.communication.models import Email
    from app.services.email.email_sending_service import EmailSendingService
    from app.services.system_actor import resolve_org_owner

    registration = await register_user(client)
    org_id = uuid.UUID(_org_id(registration))

    lead_response = await client.post(
        "/api/v1/leads",
        json={"first_name": "Grace", "last_name": "Hopper", "email": "grace@acme.example", "company_name": "Acme"},
    )
    assert lead_response.status_code == 201, lead_response.text
    lead_id = lead_response.json()["data"]["id"]

    default_mailbox = await _create_mailbox(client, name="Default", email_address="default@example.com")
    other_mailbox = await _create_mailbox(client, name="Other", email_address="other@example.com", host="smtp.other.example.com")
    assert default_mailbox.json()["data"]["is_default"] is True
    assert other_mailbox.json()["data"]["is_default"] is False
    other_mailbox_id = other_mailbox.json()["data"]["id"]

    used_hosts: list[str] = []

    class _RecordingSenderClient:
        def __init__(self, **kwargs):
            used_hosts.append(kwargs["host"])

        async def send(self, **kwargs):
            from app.services.email.sender_client import SendResult
            return SendResult(external_message_id=f"<{uuid.uuid4().hex}@test>", raw_response={})

    monkeypatch.setattr(
        "app.services.email.email_sending_service.get_sender_client",
        lambda *a, **k: _RecordingSenderClient(**k),
    )

    email = Email(
        organization_id=org_id, lead_id=uuid.UUID(lead_id), from_email="default@example.com", from_name="Default",
        to_email="lead@example.com", to_name="Lead", subject="Hi", body_html="<p>Hi</p>", body_text="Hi",
        current_status="draft", ai_generated=False, personalization_data={"sender_mailbox_id": other_mailbox_id},
    )
    db.add(email)
    await db.commit()

    actor = await resolve_org_owner(db, org_id)
    sent = await EmailSendingService(db).send_now(org_id, email.id, actor=actor)
    assert sent.current_status == "sent"
    assert used_hosts == ["smtp.other.example.com"]  # NOT the default mailbox's host


async def test_sender_mailbox_requires_manage_permission(client: AsyncClient, db: AsyncSession) -> None:
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.identity.models import Role
    from app.tests.conftest import unique_email

    registration = await register_user(client)
    role = await db.scalar(
        select(Role).where(Role.organization_id == _uuid.UUID(_org_id(registration)), Role.name == "sales")
    )
    assert role is not None
    invite = await client.post(
        "/api/v1/organizations/invitations", json={"email": unique_email("sales"), "role_id": str(role.id)}
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["meta"]["debug_invitation_token"]
    sales_client = AsyncClient(transport=client._transport, base_url="http://test")
    accepted = await sales_client.post(
        "/api/v1/organizations/invitations/accept",
        json={"token": token, "first_name": "New", "last_name": "Sales", "password": "Str0ng!Passw0rd"},
    )
    assert accepted.status_code == 201, accepted.text

    response = await sales_client.get("/api/v1/settings/email-sender/mailboxes")
    assert response.status_code == 403
