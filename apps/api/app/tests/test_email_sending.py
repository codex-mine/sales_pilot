"""
Communication -> Email Sending Infrastructure tests: DRAFT -> SENT
transitions (and idempotency), suppression (unsubscribed/bounced), daily
send limit deferral, unsubscribe token validation, the compliance footer,
retry/backoff on transient failure, bulk send partial-failure reporting,
permissions, and multi-tenancy.

The sender client and the underlying LLM client (needed to get a lead all
the way to an approved DRAFT email) are always mocked — this suite never
hits a real network, a real LLM provider, or a real SMTP server.
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai.models import AIOutput
from app.models.communication.models import Email
from app.models.crm.models import Lead
from app.repositories.user_repository import UserRepository
from app.security.tokens import create_unsubscribe_token
from app.services.ai.llm_client import LLMCompletionResult
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
        "subject": "Cutting reconciliation time", "body_html": "<p>Hi Grace, quick note.</p>",
        "body_text": "Hi Grace, quick note.", "reasoning": "Specific pain point.",
    },
]


class _StubGenerationLLMClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> LLMCompletionResult:
        self.calls.append(kwargs)
        system_prompt = kwargs.get("system_prompt", "")
        if "sales development representative" in system_prompt:
            content = json.dumps(_EMAIL_VARIANTS_JSON)
        elif "sales strategist" in system_prompt:
            content = json.dumps(_PROSPECT_JSON)
        else:
            content = json.dumps(_RESEARCH_JSON)
        return LLMCompletionResult(content=content, input_tokens=100, output_tokens=50, raw_response={})


class _StubSenderClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict] = []

    async def send(self, **kwargs):
        from app.services.email.sender_client import SendResult

        self.calls.append(kwargs)
        if self.fail:
            from app.exceptions.errors import EmailSendError

            raise EmailSendError("stubbed SMTP failure")
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
    monkeypatch.setattr(get_settings(), "outreach_smtp_username", "test-user")


def _stub_sender(monkeypatch, *, fail: bool = False) -> _StubSenderClient:
    stub = _StubSenderClient(fail=fail)
    monkeypatch.setattr("app.services.email.email_sending_service.get_sender_client", lambda *a, **k: stub)
    return stub


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


async def _create_draft_email(client: AsyncClient, db: AsyncSession, *, lead: dict | None = None) -> tuple[dict, dict]:
    """Runs the full pipeline (research -> generate -> approve) to reach an
    approved DRAFT Email, using the exact eager-mode fixtures the Research/
    Email Generation test suites already establish. Returns (lead, email)."""
    lead = lead or await _create_lead(client)
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
    assert variant is not None

    approved = await client.post(
        f"/api/v1/ai/outputs/{variant.id}/approve-email",
        json={"from_email": "sales@salespilot.app", "from_name": "SalesPilot Team"},
    )
    assert approved.status_code == 200, approved.text
    return lead, approved.json()["data"]


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


# ─── Send / idempotency ─────────────────────────────────────────────────────────


async def test_send_now_transitions_draft_to_sent_and_is_idempotent(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    stub = _stub_sender(monkeypatch)
    lead, email = await _create_draft_email(client, db)

    sent = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert sent.status_code == 200, sent.text
    data = sent.json()["data"]
    assert data["current_status"] == "sent"
    assert len(stub.calls) == 1

    # Double-submit: the row is already SENT (an "unsendable" terminal
    # status) — must not dispatch a second SMTP call.
    sent_again = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert sent_again.status_code == 200, sent_again.text
    assert sent_again.json()["data"]["current_status"] == "sent"
    assert len(stub.calls) == 1

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "contacted"


async def test_compliance_footer_present_in_sent_body(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    stub = _stub_sender(monkeypatch)
    lead, email = await _create_draft_email(client, db)

    await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    sent_call = stub.calls[0]
    assert "unsubscribe" in sent_call["body_html"].lower()
    assert "unsubscribe" in (sent_call["body_text"] or "").lower()
    # The AI-generated content never contained an unsubscribe link — proves
    # the footer was injected server-side, not present in the draft.
    assert "unsubscribe" not in _EMAIL_VARIANTS_JSON[0]["body_html"].lower()


async def test_preview_includes_footer_without_persisting(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    lead, email = await _create_draft_email(client, db)

    preview = await client.get(f"/api/v1/emails/{email['id']}/preview")
    assert preview.status_code == 200, preview.text
    assert "unsubscribe" in preview.json()["data"]["body_html"].lower()

    still_draft = await db.get(Email, uuid.UUID(email["id"]))
    assert "unsubscribe" not in still_draft.body_html.lower()  # preview never persisted


# ─── Suppression ────────────────────────────────────────────────────────────────


async def test_unsubscribed_lead_is_never_sent_to(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    stub = _stub_sender(monkeypatch)
    lead, email = await _create_draft_email(client, db)

    lead_row = await db.get(Lead, uuid.UUID(lead["id"]))
    lead_row.status = "unsubscribed"
    await db.commit()

    blocked = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert blocked.status_code == 400
    assert "unsubscribed" in blocked.json()["message"].lower() or "status" in blocked.json()["message"].lower()
    assert len(stub.calls) == 0

    failed_email = await db.get(Email, uuid.UUID(email["id"]))
    assert failed_email.current_status == "failed"
    assert failed_email.send_error


async def test_prior_hard_bounce_suppresses_send(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    stub = _stub_sender(monkeypatch)
    lead, email = await _create_draft_email(client, db)

    email_row = await db.get(Email, uuid.UUID(email["id"]))
    email_row.current_status = "bounced"  # simulate a prior hard bounce to this address
    await db.commit()

    lead2, email2 = await _create_draft_email(
        client, db, lead=await _create_lead(client, email=email_row.to_email, first_name="Grace2")
    )
    blocked = await client.post(f"/api/v1/leads/{lead2['id']}/emails/{email2['id']}/send")
    assert blocked.status_code == 400
    assert len(stub.calls) == 0


# ─── Daily send limit ───────────────────────────────────────────────────────────


async def test_daily_send_limit_defers_instead_of_failing(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    stub = _stub_sender(monkeypatch)

    async def _limit_of_one(self, organization_id):
        return 1

    monkeypatch.setattr(
        "app.services.email.email_sender_settings_service.EmailSenderSettingsService.daily_send_limit",
        _limit_of_one,
    )

    lead1, email1 = await _create_draft_email(client, db)
    first = await client.post(f"/api/v1/leads/{lead1['id']}/emails/{email1['id']}/send")
    assert first.status_code == 200
    assert first.json()["data"]["current_status"] == "sent"

    lead2, email2 = await _create_draft_email(client, db)
    second = await client.post(f"/api/v1/leads/{lead2['id']}/emails/{email2['id']}/send")
    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["current_status"] == "scheduled"  # deferred, not failed
    assert len(stub.calls) == 1


# ─── Retry / backoff ────────────────────────────────────────────────────────────


async def test_transient_failure_on_scheduled_send_reschedules_with_backoff(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    lead, email = await _create_draft_email(client, db)
    from datetime import datetime, timedelta, timezone

    scheduled_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    scheduled = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/{email['id']}/schedule", json={"scheduled_at": scheduled_at}
    )
    assert scheduled.status_code == 200, scheduled.text

    _stub_sender(monkeypatch, fail=True)
    from app.services.email.email_sending_service import EmailSendingService

    # This test is about retry/backoff bookkeeping specifically, not send-window
    # enforcement (covered implicitly elsewhere) — bypass the window check so
    # the test is deterministic regardless of what time it happens to run.
    async def _always_within_window(self, email, organization):
        return True

    monkeypatch.setattr(EmailSendingService, "_within_send_window", _always_within_window)

    scheduled_email = await db.get(Email, uuid.UUID(email["id"]))
    actor = await UserRepository(db).get_by_id(scheduled_email.sent_by)
    result = await EmailSendingService(db).process_scheduled(
        uuid.UUID(email["id"]), scheduled_email.organization_id, actor
    )
    assert result.current_status == "scheduled"  # rescheduled, not FAILED
    assert result.send_retry_count == 1
    assert result.send_error


# ─── Bulk send ──────────────────────────────────────────────────────────────────


async def test_bulk_send_reports_partial_failure(
    db: AsyncSession, client: AsyncClient, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    _stub_sender(monkeypatch)
    lead1, _email1 = await _create_draft_email(client, db)
    lead_no_draft = await _create_lead(client)

    response = await client.post(
        "/api/v1/emails/bulk-send", json={"lead_ids": [lead1["id"], lead_no_draft["id"]]}
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["requested_count"] == 2
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert any(lead_no_draft["id"] in err for err in data["errors"])


# ─── Cancel ─────────────────────────────────────────────────────────────────────


async def test_cancel_scheduled_reverts_to_draft(db: AsyncSession, client: AsyncClient, eager_generation) -> None:
    await register_user(client)
    lead, email = await _create_draft_email(client, db)
    from datetime import datetime, timedelta, timezone

    scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/schedule", json={"scheduled_at": scheduled_at})

    cancelled = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["current_status"] == "draft"


# ─── Unsubscribe ────────────────────────────────────────────────────────────────


async def test_unsubscribe_valid_token_processes_correctly(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    registration = await register_user(client)
    lead = await _create_lead(client)
    token = create_unsubscribe_token(lead["id"], _org_id(registration))

    info = await client.get(f"/api/v1/unsubscribe/{token}")
    assert info.status_code == 200
    assert info.json()["data"]["already_unsubscribed"] is False

    confirmed = await client.post(f"/api/v1/unsubscribe/{token}")
    assert confirmed.status_code == 200, confirmed.text

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "unsubscribed"

    # Re-confirming the same (still-valid) token is a safe no-op.
    info2 = await client.get(f"/api/v1/unsubscribe/{token}")
    assert info2.json()["data"]["already_unsubscribed"] is True


async def test_unsubscribe_invalid_token_rejected_generically(client: AsyncClient) -> None:
    response = await client.get("/api/v1/unsubscribe/not-a-real-token")
    assert response.status_code == 404
    assert "invalid" in response.json()["message"].lower() or "expired" in response.json()["message"].lower()


async def test_unsubscribe_requires_no_authentication(db: AsyncSession, client: AsyncClient) -> None:
    registration = await register_user(client)
    lead = await _create_lead(client)
    token = create_unsubscribe_token(lead["id"], _org_id(registration))

    anonymous_client = AsyncClient(transport=client._transport, base_url="http://test")
    response = await anonymous_client.get(f"/api/v1/unsubscribe/{token}")
    assert response.status_code == 200
    await anonymous_client.aclose()


# ─── Permissions / multi-tenancy ────────────────────────────────────────────────


async def test_viewer_cannot_send_but_can_view_outbox(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    registration = await register_user(client)
    lead, email = await _create_draft_email(client, db)
    viewer_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="viewer"
    )
    denied = await viewer_client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")
    assert denied.status_code == 403
    allowed = await viewer_client.get("/api/v1/emails/outbox")
    assert allowed.status_code == 200
    await viewer_client.aclose()


async def test_sales_role_cannot_manage_sender_settings(db: AsyncSession, client: AsyncClient) -> None:
    registration = await register_user(client)
    sales_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="sales"
    )
    denied = await sales_client.get("/api/v1/settings/email-sender")
    assert denied.status_code == 403
    await sales_client.aclose()


async def test_owner_can_connect_sender_settings(client: AsyncClient) -> None:
    await register_user(client)
    connected = await client.post(
        "/api/v1/settings/email-sender",
        json={"host": "smtp.example.com", "port": 587, "username": "user", "password": "secret", "use_tls": True},
    )
    assert connected.status_code == 200, connected.text
    data = connected.json()["data"]
    assert data["is_connected"] is True
    assert "secret" not in connected.text


async def test_multi_tenancy_isolation_on_outbox(
    client: AsyncClient, db: AsyncSession, eager_generation, monkeypatch
) -> None:
    await register_user(client)
    _stub_sender(monkeypatch)
    lead, email = await _create_draft_email(client, db)
    await client.post(f"/api/v1/leads/{lead['id']}/emails/{email['id']}/send")

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    outbox = await other_client.get("/api/v1/emails/outbox")
    assert outbox.json()["meta"]["total"] == 0
    preview = await other_client.get(f"/api/v1/emails/{email['id']}/preview")
    assert preview.status_code == 404
    await other_client.aclose()
