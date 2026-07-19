"""
Communication -> Email Open/Click Tracking & Delivery Events tests: pixel
always returns a valid image, open dedupe, click signature validation
(never an open redirector), webhook signature verification + idempotency,
hard-vs-soft bounce classification, status-never-regresses, bot-flagged
opens don't drive status/metrics, and multi-tenancy on the authenticated
read endpoints despite the public tracking/webhook endpoints being
unauthenticated.

The sender client and the underlying LLM client (needed to get a lead all
the way to a SENT email) are always mocked — this suite never hits a real
network, a real LLM provider, or a real SMTP server.
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIOutput
from app.models.communication.models import Email, EmailEvent
from app.models.crm.models import Lead
from app.security.tokens import sign_click_url
from app.services.ai.llm_client import LLMCompletionResult
from app.services.email.webhook_signature import sign_generic_webhook
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio

_RESEARCH_JSON = {
    "summary": "Acme Corp builds analytical engines.", "products_services": ["Analytical Engine Platform"],
    "target_customers": "Mid-market data teams", "business_model": "B2B SaaS", "technologies": ["Python"],
    "competitors": [], "recent_news": [], "pain_points": ["Manual reconciliation"], "sales_opportunities": [],
    "estimated_revenue": None, "funding_stage": None, "growth_signals": [],
}
_PROSPECT_JSON = {
    "buying_intent": "high", "priority_score": 80, "recommended_approach": "Lead with ROI.",
    "value_proposition": "Cut reconciliation time.", "predicted_objections": [], "likely_goals": [],
    "decision_authority": "decision_maker", "best_contact_time": "mornings",
}
_EMAIL_VARIANTS_JSON = [
    {
        "subject": "Cutting reconciliation time", "body_html": "<p>Hi Grace, <a href=\"https://example.com/pricing\">see pricing</a>.</p>",
        "body_text": "Hi Grace, see pricing: https://example.com/pricing", "reasoning": "Specific pain point.",
    },
]


class _StubGenerationLLMClient:
    async def complete(self, **kwargs) -> LLMCompletionResult:
        system_prompt = kwargs.get("system_prompt", "")
        if "sales development representative" in system_prompt:
            content = json.dumps(_EMAIL_VARIANTS_JSON)
        elif "sales strategist" in system_prompt:
            content = json.dumps(_PROSPECT_JSON)
        else:
            content = json.dumps(_RESEARCH_JSON)
        return LLMCompletionResult(content=content, input_tokens=100, output_tokens=50, raw_response={})


class _StubSenderClient:
    async def send(self, **kwargs):
        from app.services.email.sender_client import SendResult

        return SendResult(external_message_id=f"<{uuid.uuid4().hex}@test>", raw_response={})


@pytest.fixture
def eager_generation(monkeypatch):
    stub = _StubGenerationLLMClient()
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: stub)
    return stub


@pytest.fixture(autouse=True)
def mock_website_fetch(monkeypatch):
    async def _fake(self, company):
        return "", "llm_knowledge_only"

    monkeypatch.setattr(
        "app.services.ai.company_research_service.CompanyResearchService._gather_source_material", _fake
    )


@pytest.fixture(autouse=True)
def configured_sender(monkeypatch):
    monkeypatch.setattr(get_settings(), "outreach_smtp_host", "smtp.test.local")
    monkeypatch.setattr(get_settings(), "outreach_smtp_password", "test-password")
    monkeypatch.setattr("app.services.email.email_sending_service.get_sender_client", lambda *a, **k: _StubSenderClient())


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


async def _create_lead(client: AsyncClient, **overrides) -> dict:
    payload = {
        "first_name": "Grace", "last_name": "Hopper", "email": unique_email("lead"),
        "job_title": "VP Engineering", "company_name": "Acme Corp", **overrides,
    }
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_sent_email(client: AsyncClient, db: AsyncSession) -> tuple[dict, dict]:
    """Full pipeline: research -> generate -> approve -> send. Returns
    (lead, email) with the email in SENT status and a tracking_pixel_id set."""
    lead = await _create_lead(client)
    triggered = await client.post(f"/api/v1/leads/{lead['id']}/research")
    assert triggered.status_code == 200, triggered.text

    generated = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    assert generated.status_code == 200, generated.text
    job_id = generated.json()["data"]["id"]

    variant = await db.scalar(
        select(AIOutput).where(AIOutput.job_id == uuid.UUID(job_id), AIOutput.output_type == "email_variant")
    )
    approved = await client.post(
        f"/api/v1/ai/outputs/{variant.id}/approve-email",
        json={"from_email": "sales@salespilot.app", "from_name": "SalesPilot Team"},
    )
    assert approved.status_code == 200, approved.text
    email = approved.json()["data"]

    sent = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert sent.status_code == 200, sent.text
    return lead, sent.json()["data"]


async def _invite_and_accept(client: AsyncClient, db: AsyncSession, *, organization_id: str, role_name: str) -> AsyncClient:
    from app.models.identity.models import Role

    role = await db.scalar(
        select(Role).where(Role.organization_id == uuid.UUID(organization_id), Role.name == role_name)
    )
    assert role is not None
    invite = await client.post(
        "/api/v1/organizations/invitations",
        json={"email": unique_email(role_name), "role_id": str(role.id)},
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


# ─── Open pixel ─────────────────────────────────────────────────────────────────


async def test_pixel_always_returns_valid_image_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/track/open/not-a-real-pixel-id.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


async def test_pixel_records_open_and_advances_status(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id
    assert pixel_id

    response = await client.get(
        f"/api/v1/track/open/{pixel_id}.png", headers={"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    assert response.status_code == 200

    await db.refresh(email_row)
    assert email_row.current_status == "opened"
    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "opened"


async def test_duplicate_pixel_fires_within_dedupe_window_do_not_duplicate(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id

    for _ in range(3):
        response = await client.get(
            f"/api/v1/track/open/{pixel_id}.png",
            headers={"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )
        assert response.status_code == 200

    events = await db.scalars(
        select(EmailEvent).where(EmailEvent.email_id == email_row.id, EmailEvent.event_type == "opened")
    )
    assert len(list(events)) == 1


async def test_bot_flagged_open_recorded_but_does_not_advance_lead_status(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id

    response = await client.get(
        f"/api/v1/track/open/{pixel_id}.png",
        headers={"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
    )
    assert response.status_code == 200

    events = await db.scalars(
        select(EmailEvent).where(EmailEvent.email_id == email_row.id, EmailEvent.event_type == "opened")
    )
    event_list = list(events)
    assert len(event_list) == 1
    assert event_list[0].metadata_ == {"likely_bot": True}

    await db.refresh(email_row)
    assert email_row.current_status == "sent"  # not advanced to "opened"
    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "contacted"  # not advanced to "opened"


# ─── Click redirect ─────────────────────────────────────────────────────────────


async def test_click_with_valid_signature_redirects_and_records_event(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id
    url = "https://example.com/pricing"
    sig = sign_click_url(pixel_id, url)

    response = await client.get(
        f"/api/v1/track/click/{pixel_id}", params={"url": url, "sig": sig}, follow_redirects=False,
        headers={"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    assert response.status_code == 302
    assert response.headers["location"] == url

    await db.refresh(email_row)
    assert email_row.current_status == "clicked"
    events = await db.scalars(select(EmailEvent).where(EmailEvent.email_id == email_row.id))
    event_types = {e.event_type for e in events}
    assert "clicked" in event_types
    assert "opened" in event_types  # click backfills an open


async def test_click_with_tampered_url_never_follows_unsigned_target(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id
    legit_sig = sign_click_url(pixel_id, "https://example.com/pricing")

    response = await client.get(
        f"/api/v1/track/click/{pixel_id}",
        params={"url": "https://evil.example.com/phish", "sig": legit_sig},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] != "https://evil.example.com/phish"
    assert "evil.example.com" not in response.headers["location"]

    events = await db.scalars(select(EmailEvent).where(EmailEvent.email_id == email_row.id, EmailEvent.event_type == "clicked"))
    assert list(events) == []  # invalid signature never recorded an event either


async def test_click_with_unknown_pixel_id_redirects_safely(client: AsyncClient) -> None:
    fake_pixel_id = "not-a-real-pixel"
    sig = sign_click_url(fake_pixel_id, "https://example.com/pricing")
    response = await client.get(
        f"/api/v1/track/click/{fake_pixel_id}",
        params={"url": "https://example.com/pricing", "sig": sig},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] != "https://example.com/pricing"


# ─── Delivery webhook ───────────────────────────────────────────────────────────


def _webhook_body(**overrides) -> bytes:
    payload = {
        "event_type": "delivered", "message_id": "irrelevant", "event_id": str(uuid.uuid4()),
        "timestamp": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


async def test_webhook_rejects_unsigned_payload(client: AsyncClient) -> None:
    body = _webhook_body()
    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401


async def test_webhook_rejects_forged_signature(client: AsyncClient) -> None:
    body = _webhook_body()
    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": "0" * 64},
    )
    assert response.status_code == 401


async def test_webhook_valid_signature_delivered_advances_status(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    body = _webhook_body(event_type="delivered", message_id=email_row.external_message_id)
    sig = sign_generic_webhook(body)

    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )
    assert response.status_code == 200, response.text

    await db.refresh(email_row)
    assert email_row.current_status == "delivered"


async def test_webhook_idempotent_on_redelivery(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    event_id = str(uuid.uuid4())
    body = _webhook_body(event_type="delivered", message_id=email_row.external_message_id, event_id=event_id)
    sig = sign_generic_webhook(body)

    for _ in range(2):
        response = await client.post(
            "/api/v1/webhooks/email/generic", content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
        )
        assert response.status_code == 200

    events = await db.scalars(
        select(EmailEvent).where(EmailEvent.email_id == email_row.id, EmailEvent.event_type == "delivered")
    )
    assert len(list(events)) == 1


async def test_hard_bounce_suppresses_lead_soft_bounce_does_not(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    lead1, email1 = await _create_sent_email(client, db)
    email1_row = await db.get(Email, uuid.UUID(email1["id"]))
    body = _webhook_body(event_type="bounced", message_id=email1_row.external_message_id, bounce_type="hard", reason="mailbox does not exist")
    sig = sign_generic_webhook(body)
    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )
    assert response.status_code == 200

    lead1_after = (await client.get(f"/api/v1/leads/{lead1['id']}")).json()["data"]
    assert lead1_after["status"] == "bounced"
    await db.refresh(email1_row)
    assert email1_row.current_status == "bounced"

    lead2, email2 = await _create_sent_email(client, db)
    email2_row = await db.get(Email, uuid.UUID(email2["id"]))
    body2 = _webhook_body(event_type="bounced", message_id=email2_row.external_message_id, bounce_type="soft", reason="mailbox full")
    sig2 = sign_generic_webhook(body2)
    response2 = await client.post(
        "/api/v1/webhooks/email/generic", content=body2,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig2},
    )
    assert response2.status_code == 200

    lead2_after = (await client.get(f"/api/v1/leads/{lead2['id']}")).json()["data"]
    assert lead2_after["status"] != "bounced"  # soft bounce does not suppress


async def test_complaint_suppresses_lead_distinctly_from_unsubscribe(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    body = _webhook_body(event_type="complained", message_id=email_row.external_message_id)
    sig = sign_generic_webhook(body)
    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )
    assert response.status_code == 200

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "unsubscribed"


async def test_status_never_regresses_late_delivered_after_opened(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))
    pixel_id = email_row.tracking_pixel_id

    await client.get(
        f"/api/v1/track/open/{pixel_id}.png",
        headers={"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    await db.refresh(email_row)
    assert email_row.current_status == "opened"

    body = _webhook_body(event_type="delivered", message_id=email_row.external_message_id)
    sig = sign_generic_webhook(body)
    response = await client.post(
        "/api/v1/webhooks/email/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )
    assert response.status_code == 200

    await db.refresh(email_row)
    assert email_row.current_status == "opened"  # late DELIVERED did not revert the status


# ─── Authenticated read endpoints + multi-tenancy ────────────────────────────────


async def test_email_events_and_timeline_endpoints(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)

    events = await client.get(f"/api/v1/emails/{email['id']}/events")
    assert events.status_code == 200
    assert len(events.json()["data"]) >= 1

    timeline = await client.get(f"/api/v1/emails/{email['id']}/timeline")
    assert timeline.status_code == 200
    data = timeline.json()["data"]
    assert data["email_id"] == email["id"]
    assert data["current_status"] == "sent"


async def test_multi_tenancy_isolation_on_events(client: AsyncClient, db: AsyncSession, eager_generation) -> None:
    await register_user(client)
    _lead, email = await _create_sent_email(client, db)

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    events = await other_client.get(f"/api/v1/emails/{email['id']}/events")
    assert events.status_code == 404
    await other_client.aclose()


async def test_viewer_can_read_events_but_not_manage(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    registration = await register_user(client)
    _lead, email = await _create_sent_email(client, db)
    viewer_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="viewer"
    )
    events = await viewer_client.get(f"/api/v1/emails/{email['id']}/events")
    assert events.status_code == 200
    await viewer_client.aclose()


async def test_email_performance_analytics_endpoint(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    await register_user(client)
    _lead, _email = await _create_sent_email(client, db)

    response = await client.get("/api/v1/analytics/email-performance")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_sent"] >= 0
    assert "open_rate" in data and "click_rate" in data and "bounce_rate" in data
