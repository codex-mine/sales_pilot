"""
Phase X Issue 08 -> Send Custom Email from Lead Detail: composing a manual
email creates a real Email row (identical tracking to any other), respects
an explicitly-chosen sender mailbox, defaults the recipient to the lead's own
address, can be sent immediately or saved as a draft for later, and never
interferes with the AI-generation or campaign-sequence creation paths.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


class _StubSenderClient:
    async def send(self, **kwargs):
        from app.services.email.sender_client import SendResult

        return SendResult(external_message_id=f"<{uuid.uuid4().hex}@test>", raw_response={})


@pytest.fixture(autouse=True)
def configured_sender(monkeypatch):
    monkeypatch.setattr(get_settings(), "outreach_smtp_host", "smtp.test.local")
    monkeypatch.setattr(get_settings(), "outreach_smtp_password", "test-password")
    monkeypatch.setattr("app.services.email.email_sending_service.get_sender_client", lambda *a, **k: _StubSenderClient())


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


async def _create_lead(client: AsyncClient, **overrides) -> dict:
    payload = {
        "first_name": "Grace", "last_name": "Hopper", "email": "grace@acme.example",
        "company_name": "Acme Corp", **overrides,
    }
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_compose_and_send_immediately(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose",
        json={"subject": "Quick note", "body_html": "<p>Hi there</p>", "body_text": "Hi there"},
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["current_status"] == "sent"
    assert data["to_email"] == "grace@acme.example"  # defaulted from the lead
    assert data["ai_generated"] is False
    assert data["subject"] == "Quick note"


async def test_compose_saves_as_draft_when_send_now_false(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose",
        json={"subject": "Draft me", "body_html": "<p>Draft</p>", "send_now": False},
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["current_status"] == "draft"

    # Appears in the same drafts list AI-generated emails use.
    drafts = await client.get(f"/api/v1/leads/{lead['id']}/emails/drafts")
    assert any(e["subject"] == "Draft me" for e in drafts.json()["data"])


async def test_compose_requires_recipient_when_lead_has_no_email(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client, email=None)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose",
        json={"subject": "Hi", "body_html": "<p>Hi</p>"},
    )
    assert response.status_code == 400, response.text


async def test_compose_accepts_explicit_recipient_override(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client, email=None)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose",
        json={"subject": "Hi", "body_html": "<p>Hi</p>", "to_email": "override@example.com", "send_now": False},
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["to_email"] == "override@example.com"


async def test_compose_uses_explicitly_chosen_sender_mailbox(client: AsyncClient, db: AsyncSession, monkeypatch) -> None:
    """Same fake-SMTP mailbox-creation pattern as test_sender_mailboxes.py —
    proves the compose endpoint actually threads `sender_mailbox_id` through
    to send-time credential resolution, not just storing it cosmetically."""
    import smtplib

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None, context=None):
            self.host = host

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context=None):
            pass

        def login(self, username, password):
            pass

        def noop(self):
            pass

        def send_message(self, message):
            pass

    monkeypatch.setattr("app.services.email.sender_client.smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("app.services.email.sender_client.smtplib.SMTP_SSL", _FakeSMTP)

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

    await register_user(client)
    lead = await _create_lead(client)

    mailbox = await client.post(
        "/api/v1/settings/email-sender/mailboxes",
        json={
            "name": "Support", "email_address": "support@example.com", "host": "smtp.support.example.com",
            "port": 587, "username": "support@example.com", "password": "pw", "encryption_type": "starttls",
        },
    )
    assert mailbox.status_code == 201, mailbox.text
    mailbox_id = mailbox.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose",
        json={"subject": "Hi", "body_html": "<p>Hi</p>", "sender_mailbox_id": mailbox_id},
    )
    assert response.status_code == 201, response.text
    assert used_hosts == ["smtp.support.example.com"]
    assert response.json()["data"]["from_email"] == "support@example.com"


async def test_compose_scoped_to_organization(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    response = await other_client.post(
        f"/api/v1/leads/{lead['id']}/emails/compose", json={"subject": "Hi", "body_html": "<p>Hi</p>"}
    )
    assert response.status_code == 404
