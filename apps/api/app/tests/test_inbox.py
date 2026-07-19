"""
Communication -> Inbox & AI Reply Classification tests: inbound webhook
ingestion for two provider shapes (generic + postmark), idempotency on
redelivery, in-reply-to threading, AI classification (including out-of-enum
coercion), classification side effects (INTERESTED/MEETING_REQUESTED/
UNSUBSCRIBE_REQUEST status transitions, status-never-regresses), unmatched
sender handling (stub Lead + UNKNOWN flag), manual reclassification distinct
from AI classification, owner notification, multi-tenancy, and permissions.

Like `test_email_tracking.py`, the sender client and the LLM client are
always stubbed — this suite never hits a real network, LLM provider, or SMTP
server.
"""

import base64
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIOutput
from app.models.communication.models import Email, Message
from app.models.crm.models import Lead
from app.models.identity.models import Organization, Role
from app.models.remaining_domains import Notification
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
        "subject": "Cutting reconciliation time", "body_html": "<p>Hi Grace, see pricing.</p>",
        "body_text": "Hi Grace, see pricing.", "reasoning": "Specific pain point.",
    },
]
_ORG_SEND_ADDRESS = "sales@salespilot.app"


class _StubLLMClient:
    def __init__(self) -> None:
        self.classification_response: dict = {
            "classification": "interested", "confidence": 0.87, "suggested_action": "Send pricing details.",
        }

    async def complete(self, **kwargs) -> LLMCompletionResult:
        system_prompt = kwargs.get("system_prompt", "")
        if "reply classifier" in system_prompt:
            content = json.dumps(self.classification_response)
        elif "sales development representative" in system_prompt:
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
def eager_ai(monkeypatch) -> _StubLLMClient:
    stub = _StubLLMClient()
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
    (lead, email) with the email in SENT status, from `_ORG_SEND_ADDRESS` to
    the lead's own address — the correspondence pair the Inbox module's
    primary tenant-resolution path matches against."""
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
        json={"from_email": _ORG_SEND_ADDRESS, "from_name": "SalesPilot Team"},
    )
    assert approved.status_code == 200, approved.text
    email = approved.json()["data"]

    sent = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert sent.status_code == 200, sent.text
    return lead, sent.json()["data"]


async def _invite_and_accept(client: AsyncClient, db: AsyncSession, *, organization_id: str, role_name: str) -> AsyncClient:
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


def _generic_body(**overrides) -> bytes:
    payload = {
        "from_email": "grace@prospect.test", "from_name": "Grace Hopper", "to_email": _ORG_SEND_ADDRESS,
        "subject": "Re: Cutting reconciliation time", "body_text": "Sounds great, let's talk!",
        "body_html": "<p>Sounds great, let's talk!</p>", "message_id": f"<{uuid.uuid4().hex}@prospect.test>",
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


def _postmark_body(**overrides) -> dict:
    payload = {
        "FromFull": {"Email": "grace@prospect.test", "Name": "Grace Hopper"},
        "ToFull": [{"Email": _ORG_SEND_ADDRESS, "Name": "Sales"}],
        "Subject": "Re: Cutting reconciliation time",
        "TextBody": "Sounds great, let's talk!",
        "HtmlBody": "<p>Sounds great, let's talk!</p>",
        "MessageID": f"{uuid.uuid4().hex}",
        "Headers": [],
    }
    payload.update(overrides)
    return payload


def _basic_auth_header(password: str) -> str:
    token = base64.b64encode(f"inbound:{password}".encode()).decode()
    return f"Basic {token}"


async def _post_generic(client: AsyncClient, body: bytes) -> "httpx.Response":  # noqa: F821
    sig = sign_generic_webhook(body)
    return await client.post(
        "/api/v1/webhooks/email/inbound/generic", content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )


# ─── Ingestion: generic + postmark ───────────────────────────────────────────────


async def test_generic_inbound_webhook_ingests_reply_and_classifies(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200, response.text

    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))
    assert message is not None
    assert message.reply_classification == "interested"
    assert message.ai_confidence == pytest.approx(0.87)
    assert message.ai_suggested_action == "Send pricing details."

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "interested"

    email_row = await db.get(Email, uuid.UUID(email["id"]))
    conversation_id = email_row.conversation_id
    assert conversation_id is not None
    assert message.conversation_id == conversation_id


async def test_postmark_inbound_webhook_ingests_reply(
    db: AsyncSession, client: AsyncClient, eager_ai, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "inbound_email_basic_auth_password", "postmark-secret")
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)

    payload = _postmark_body(FromFull={"Email": lead["email"], "Name": "Grace Hopper"})
    response = await client.post(
        "/api/v1/webhooks/email/inbound/postmark", json=payload,
        headers={"Authorization": _basic_auth_header("postmark-secret")},
    )
    assert response.status_code == 200, response.text

    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))
    assert message is not None
    assert message.body_text == "Sounds great, let's talk!"


async def test_postmark_webhook_rejects_wrong_basic_auth_password(
    db: AsyncSession, client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "inbound_email_basic_auth_password", "postmark-secret")
    await register_user(client)
    payload = _postmark_body()
    response = await client.post(
        "/api/v1/webhooks/email/inbound/postmark", json=payload,
        headers={"Authorization": _basic_auth_header("wrong-password")},
    )
    assert response.status_code == 401


async def test_generic_inbound_webhook_rejects_unsigned_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/webhooks/email/inbound/generic", content=_generic_body(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401


async def test_unsupported_inbound_provider_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/webhooks/email/inbound/unknown-esp", content=_generic_body(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401


async def test_idempotent_on_redelivered_external_message_id(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    body = _generic_body(from_email=lead["email"], message_id="<redelivered@prospect.test>")

    for _ in range(2):
        response = await _post_generic(client, body)
        assert response.status_code == 200

    count = await db.scalar(
        select(func.count()).select_from(Message).where(Message.lead_id == uuid.UUID(lead["id"]))
    )
    assert count == 1


async def test_threading_resolves_via_in_reply_to_header(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)
    email_row = await db.get(Email, uuid.UUID(email["id"]))

    response = await _post_generic(
        client, _generic_body(from_email=lead["email"], in_reply_to=email_row.external_message_id)
    )
    assert response.status_code == 200

    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))
    assert message.in_reply_to_email_id == email_row.id


# ─── Classification side effects ─────────────────────────────────────────────────


async def test_meeting_requested_classification_advances_lead_status(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    eager_ai.classification_response = {
        "classification": "meeting_requested", "confidence": 0.95, "suggested_action": "Propose times.",
    }
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "interested"


async def test_unsubscribe_request_classification_suppresses_lead(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    eager_ai.classification_response = {
        "classification": "unsubscribe_request", "confidence": 0.99, "suggested_action": "Do not contact again.",
    }
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "unsubscribed"


async def test_ai_classification_out_of_enum_coerced_to_unknown(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    eager_ai.classification_response = {
        "classification": "extremely_excited", "confidence": 0.5, "suggested_action": "n/a",
    }
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200

    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))
    assert message.reply_classification == "unknown"


async def test_status_never_regresses_reply_after_qualified(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    advanced = await client.patch(f"/api/v1/leads/{lead['id']}", json={"status": "qualified"})
    assert advanced.status_code == 200, advanced.text

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "qualified"  # not regressed to "replied"/"interested"


# ─── Unmatched sender ─────────────────────────────────────────────────────────────


async def test_unmatched_sender_creates_stub_lead_and_flags_unknown(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    registration = await register_user(client)
    org = await db.get(Organization, uuid.UUID(_org_id(registration)))
    org.domain = f"acme-{uuid.uuid4().hex[:8]}.test"
    await db.commit()

    stranger_email = unique_email("stranger")
    body = _generic_body(
        from_email=stranger_email, from_name="A Stranger", to_email=f"hello@{org.domain}",
        message_id=f"<{uuid.uuid4().hex}@stranger.test>",
    )
    response = await _post_generic(client, body)
    assert response.status_code == 200, response.text

    stub_lead = await db.scalar(select(Lead).where(Lead.email == stranger_email))
    assert stub_lead is not None
    assert stub_lead.source == "inbound_reply"

    message = await db.scalar(select(Message).where(Message.lead_id == stub_lead.id))
    assert message is not None
    assert message.reply_classification == "unknown"
    assert "unmatched" in (message.ai_suggested_action or "").lower()
    # Unmatched replies never go through AI classification (no lead to attribute confidence/side-effects to).
    assert message.ai_classified_at is None


async def test_unattributable_webhook_silently_dropped(client: AsyncClient) -> None:
    body = _generic_body(
        from_email=unique_email("nobody"), to_email="unrelated@nowhere-registered.test",
        message_id=f"<{uuid.uuid4().hex}@nobody.test>",
    )
    response = await _post_generic(client, body)
    assert response.status_code == 200  # never leaks whether a tenant exists


# ─── Owner notification ────────────────────────────────────────────────────────────


async def test_notification_created_for_lead_owner(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    registration = await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    owner_id = registration["data"]["id"]
    assigned = await client.patch(f"/api/v1/leads/{lead['id']}", json={"owner_id": owner_id})
    assert assigned.status_code == 200, assigned.text

    response = await _post_generic(client, _generic_body(from_email=lead["email"]))
    assert response.status_code == 200

    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))
    notification = await db.scalar(
        select(Notification).where(Notification.entity_id == message.id, Notification.entity_type == "message")
    )
    assert notification is not None
    assert notification.notification_type == "new_reply"
    assert notification.user_id == uuid.UUID(owner_id)


# ─── Read endpoints + manual reclassification ─────────────────────────────────────


async def test_conversation_list_and_detail_endpoints(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    await register_user(client)
    lead, email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))

    listing = await client.get("/api/v1/inbox/conversations")
    assert listing.status_code == 200, listing.text
    items = listing.json()["data"]
    assert len(items) == 1
    assert items[0]["lead_id"] == lead["id"]
    assert items[0]["latest_classification"] == "interested"

    conversation_id = items[0]["id"]
    detail = await client.get(f"/api/v1/inbox/conversations/{conversation_id}")
    assert detail.status_code == 200, detail.text
    thread_items = detail.json()["data"]["items"]
    directions = [item["direction"] for item in thread_items]
    assert directions == ["outbound", "inbound"]  # chronologically sorted
    assert thread_items[0]["id"] == email["id"]

    mark_read = await client.patch(f"/api/v1/inbox/conversations/{conversation_id}/read", json={"is_read": True})
    assert mark_read.status_code == 200
    assert mark_read.json()["data"]["items"][-1]["is_read"] is True


async def test_default_conversation_list_excludes_spam(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    eager_ai.classification_response = {"classification": "spam", "confidence": 0.6, "suggested_action": "Ignore."}
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))

    default_listing = await client.get("/api/v1/inbox/conversations")
    assert default_listing.json()["data"] == []

    explicit_listing = await client.get("/api/v1/inbox/conversations", params={"classification": "spam"})
    assert len(explicit_listing.json()["data"]) == 1


async def test_manual_reclassify_overrides_ai_classification(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    eager_ai.classification_response = {
        "classification": "not_interested", "confidence": 0.7, "suggested_action": "Move on.",
    }
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))
    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))

    reclassified = await client.patch(
        f"/api/v1/inbox/messages/{message.id}/classification", json={"classification": "interested"}
    )
    assert reclassified.status_code == 200, reclassified.text
    assert reclassified.json()["data"]["reply_classification"] == "interested"

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "interested"  # side effect applied on manual reclassification too


async def test_manual_reclassify_rejects_invalid_classification(
    db: AsyncSession, client: AsyncClient, eager_ai
) -> None:
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))
    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))

    response = await client.patch(
        f"/api/v1/inbox/messages/{message.id}/classification", json={"classification": "not-a-real-value"}
    )
    assert response.status_code == 400


async def test_get_lead_conversations_endpoint(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))

    response = await client.get(f"/api/v1/leads/{lead['id']}/conversations")
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1


# ─── Multi-tenancy + permissions ───────────────────────────────────────────────────


async def test_multi_tenancy_isolation_on_conversations(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))
    conversation_id = (await client.get("/api/v1/inbox/conversations")).json()["data"][0]["id"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    cross_tenant = await other_client.get(f"/api/v1/inbox/conversations/{conversation_id}")
    assert cross_tenant.status_code == 404
    empty_listing = await other_client.get("/api/v1/inbox/conversations")
    assert empty_listing.json()["data"] == []
    await other_client.aclose()


async def test_viewer_can_read_inbox_but_not_reclassify(db: AsyncSession, client: AsyncClient, eager_ai) -> None:
    registration = await register_user(client)
    lead, _email = await _create_sent_email(client, db)
    await _post_generic(client, _generic_body(from_email=lead["email"]))
    message = await db.scalar(select(Message).where(Message.lead_id == uuid.UUID(lead["id"])))

    viewer_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="viewer"
    )
    listing = await viewer_client.get("/api/v1/inbox/conversations")
    assert listing.status_code == 200

    forbidden = await viewer_client.patch(
        f"/api/v1/inbox/messages/{message.id}/classification", json={"classification": "interested"}
    )
    assert forbidden.status_code == 403
    await viewer_client.aclose()
