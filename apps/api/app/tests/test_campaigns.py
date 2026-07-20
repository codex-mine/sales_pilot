"""
Campaigns -> Multi-Step Sequence Automation tests: the scheduler's
`SELECT ... FOR UPDATE SKIP LOCKED` claim is mutually exclusive under real
concurrency, auto-stop halts a sequence the moment a lead replies/
unsubscribes/bounces, conditional skip logic reuses the existing engagement-
ordering helpers, send-window rollforward avoids off-hours firing,
requires_approval=True stalls at DRAFT until approval resumes the sequence
via `advance_after_send`, enrollment uniqueness, `enroll_by_filter` reusing
`LeadRepository`'s own filters, and permissions/multi-tenancy.

The sender client and LLM client are always stubbed — this suite never hits
a real network, SMTP server, or LLM provider.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.campaigns.models import CampaignLead, EmailTemplate
from app.models.communication.models import Email
from app.models.crm.models import Lead
from app.models.identity.models import Role
from app.repositories.campaign_lead_repository import CampaignLeadRepository
from app.repositories.email_template_repository import EmailTemplateRepository
from app.services.ai.llm_client import LLMCompletionResult
from app.services.campaigns.campaign_scheduler_service import CampaignSchedulerService
from app.tests.conftest import TEST_DATABASE_URL, register_user, unique_email

pytestmark = pytest.mark.asyncio


class _StubSenderClient:
    async def send(self, **kwargs):
        from app.services.email.sender_client import SendResult

        return SendResult(external_message_id=f"<{uuid.uuid4().hex}@test>", raw_response={})


class _StubGenerationLLMClient:
    async def complete(self, **kwargs) -> LLMCompletionResult:
        system_prompt = kwargs.get("system_prompt", "")
        if "sales development representative" in system_prompt:
            content = json.dumps([
                {"subject": "Quick question", "body_html": "<p>Hi {{ first }}</p>", "body_text": "Hi",
                 "reasoning": "test"}
            ])
        elif "sales strategist" in system_prompt:
            content = json.dumps({
                "buying_intent": "high", "priority_score": 80, "recommended_approach": "Lead with ROI.",
                "value_proposition": "Cut costs.", "predicted_objections": [], "likely_goals": [],
                "decision_authority": "decision_maker", "best_contact_time": "mornings",
            })
        else:
            content = json.dumps({
                "summary": "Acme builds widgets.", "products_services": ["Widgets"],
                "target_customers": "SMBs", "business_model": "B2B", "technologies": [],
                "competitors": [], "recent_news": [], "pain_points": [], "sales_opportunities": [],
                "estimated_revenue": None, "funding_stage": None, "growth_signals": [],
            })
        return LLMCompletionResult(content=content, input_tokens=50, output_tokens=20, raw_response={})


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


async def _create_campaign(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": f"Campaign {uuid.uuid4().hex[:8]}", "goal": "Book demos",
        "send_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "send_start_hour": 0, "send_end_hour": 23, "daily_send_limit": 50,
        "requires_approval": True, **overrides,
    }
    response = await client.post("/api/v1/campaigns", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_sequence(client: AsyncClient, campaign_id: str, **overrides) -> dict:
    payload = {"name": "Main sequence", **overrides}
    response = await client.post(f"/api/v1/campaigns/{campaign_id}/sequences", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_template(db: AsyncSession, organization_id: str) -> EmailTemplate:
    template = await EmailTemplateRepository(db).create(
        organization_id=uuid.UUID(organization_id), created_by=None,
        name="Cold outreach template", template_type="cold_outreach", tone="professional",
        subject="Hi {{ lead.first_name }}", body_html="<p>Hi {{ lead.first_name }} from {{ company.name }}</p>",
        body_text="Hi {{ lead.first_name }}", is_active=True,
    )
    await db.commit()
    return template


async def _create_email_step(
    client: AsyncClient, sequence_id: str, *, step_order: int, template_id: str | None,
    content_source: str = "template", delay_days: int = 0, condition: dict | None = None,
) -> dict:
    payload = {
        "step_type": "email", "step_order": step_order, "delay_days": delay_days,
        "content_source": content_source, "condition": condition,
    }
    if template_id:
        payload["email_template_id"] = template_id
    response = await client.post(f"/api/v1/sequences/{sequence_id}/steps", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


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


async def _full_send_now_setup(client: AsyncClient, db: AsyncSession, org_id: str, *, requires_approval: bool) -> tuple[dict, dict, dict]:
    """Campaign (active) -> sequence -> single template email step -> enrolled lead, due now."""
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client, requires_approval=requires_approval)
    activated = await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    assert activated.status_code == 200, activated.text
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    assert enrolled.status_code == 201, enrolled.text
    campaign_lead = enrolled.json()["data"]

    # force due-now for a deterministic test (enrollment normally computes a
    # near-future next_action_at rolled into the send window)
    row = await db.get(CampaignLead, uuid.UUID(campaign_lead["id"]))
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    return campaign, lead, campaign_lead


# ─── Campaign CRUD + status control ──────────────────────────────────────────────


async def test_create_and_read_campaign(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)
    assert campaign["status"] == "draft"
    assert campaign["requires_approval"] is True

    response = await client.get(f"/api/v1/campaigns/{campaign['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == campaign["name"]


async def test_update_campaign_requires_approval_flag(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client, requires_approval=True)
    response = await client.patch(f"/api/v1/campaigns/{campaign['id']}", json={"requires_approval": False})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["requires_approval"] is False


async def test_activate_pause_archive_lifecycle(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)

    cannot_pause = await client.post(f"/api/v1/campaigns/{campaign['id']}/pause")
    assert cannot_pause.status_code == 400

    activated = await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "active"
    assert activated.json()["data"]["started_at"] is not None

    paused = await client.post(f"/api/v1/campaigns/{campaign['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["data"]["status"] == "paused"

    archived = await client.post(f"/api/v1/campaigns/{campaign['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"


async def test_delete_active_campaign_rejected(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    response = await client.delete(f"/api/v1/campaigns/{campaign['id']}")
    assert response.status_code == 400


# ─── Sequence / step CRUD + validation ────────────────────────────────────────────


async def test_step_type_rejects_unsupported(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    response = await client.post(
        f"/api/v1/sequences/{sequence['id']}/steps",
        json={"step_type": "linkedin_message", "step_order": 1},
    )
    # Pydantic field_validator raising ValueError surfaces as FastAPI's
    # automatic 422 request-validation response — same shape as every other
    # choice-field validator in this codebase (e.g. Lead/Company status).
    assert response.status_code == 422
    assert "not yet supported" in response.text.lower()


async def test_step_order_conflict_returns_clear_error(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    registration_org = _org_id(registration)
    template = await _create_template(db, registration_org)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    response = await client.post(
        f"/api/v1/sequences/{sequence['id']}/steps",
        json={"step_type": "wait", "step_order": 1, "delay_days": 1},
    )
    assert response.status_code == 400
    assert response.json()["errors"] is not None


async def test_email_step_requires_template_or_ai(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    response = await client.post(
        f"/api/v1/sequences/{sequence['id']}/steps",
        json={"step_type": "email", "step_order": 1, "content_source": "template"},
    )
    assert response.status_code == 400


async def test_move_step_reorders(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    registration_org = _org_id(registration)
    template = await _create_template(db, registration_org)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    step1 = await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    step2 = await client.post(
        f"/api/v1/sequences/{sequence['id']}/steps", json={"step_type": "wait", "step_order": 2, "delay_days": 1}
    )
    step2 = step2.json()["data"]

    moved = await client.post(f"/api/v1/sequence-steps/{step2['id']}/move", params={"direction": "up"})
    assert moved.status_code == 200, moved.text
    ordered = moved.json()["data"]
    assert ordered[0]["id"] == step2["id"]
    assert ordered[1]["id"] == step1["id"]


# ─── Enrollment ─────────────────────────────────────────────────────────────────


async def test_enroll_lead_respects_uniqueness(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    registration_org = _org_id(registration)
    template = await _create_template(db, registration_org)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    lead = await _create_lead(client)

    first = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    assert first.status_code == 201

    second = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    assert second.status_code == 400
    assert "already enrolled" in second.text.lower()


async def test_enroll_without_sequence_rejected(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)
    lead = await _create_lead(client)
    response = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    assert response.status_code == 400


async def test_enroll_by_filter_reuses_lead_filters(client: AsyncClient, db: AsyncSession) -> None:
    """Only leads matching the filter (job_title search) get enrolled — proof
    `enroll_by_filter` actually applies `LeadRepository.list_for_organization`'s
    filters rather than enrolling everyone."""
    registration = await register_user(client)
    registration_org = _org_id(registration)
    template = await _create_template(db, registration_org)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))

    matching = await _create_lead(client, job_title="VP of Sales")
    _non_matching = await _create_lead(client, job_title="Software Engineer")

    response = await client.post(
        f"/api/v1/campaigns/{campaign['id']}/enroll/by-filter", json={"search": "VP of Sales"}
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["enrolled_count"] == 1

    campaign_leads = (await client.get(f"/api/v1/campaigns/{campaign['id']}/leads")).json()["data"]
    assert len(campaign_leads) == 1
    assert campaign_leads[0]["lead"]["id"] == matching["id"]


async def test_unenroll_lead(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    registration_org = _org_id(registration)
    template = await _create_template(db, registration_org)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = enrolled.json()["data"]["id"]

    response = await client.delete(f"/api/v1/campaign-leads/{campaign_lead_id}", params={"reason": "test"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "opted_out"
    assert response.json()["data"]["next_action_at"] is None


# ─── Send-window rollforward ──────────────────────────────────────────────────────


def test_roll_forward_into_window_avoids_off_hours() -> None:
    from app.services.campaigns.send_window import roll_forward_into_window

    saturday_2pm = datetime(2026, 7, 25, 14, 0, tzinfo=timezone.utc)  # a Saturday
    result = roll_forward_into_window(
        saturday_2pm, send_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        send_start_hour=9, send_end_hour=17, tz_name="UTC",
    )
    assert result.weekday() == 0  # Monday
    assert result.hour == 9

    weekday_11pm = datetime(2026, 7, 20, 23, 0, tzinfo=timezone.utc)  # a Monday, after hours
    result2 = roll_forward_into_window(
        weekday_11pm, send_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        send_start_hour=9, send_end_hour=17, tz_name="UTC",
    )
    assert result2.date() == datetime(2026, 7, 21).date()
    assert result2.hour == 9


# ─── Scheduler: execute_step end-to-end (called directly, not via Celery) ────────


async def test_execute_step_stalls_at_draft_when_requires_approval(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    _campaign, lead, campaign_lead = await _full_send_now_setup(client, db, _org_id(registration), requires_approval=True)

    await CampaignSchedulerService(db).execute_step(uuid.UUID(campaign_lead["id"]))

    row = await db.get(CampaignLead, uuid.UUID(campaign_lead["id"]))
    assert row.status == "in_progress"
    assert row.next_action_at is None  # stalled — waiting on manual approval

    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert email is not None
    assert email.current_status == "draft"
    assert email.campaign_lead_id == row.id


async def test_approving_stalled_draft_resumes_sequence_via_advance_after_send(
    client: AsyncClient, db: AsyncSession
) -> None:
    registration = await register_user(client)
    org_id = _org_id(registration)
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client, requires_approval=True)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    await _create_email_step(client, sequence["id"], step_order=2, template_id=str(template.id), delay_days=2)
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = uuid.UUID(enrolled.json()["data"]["id"])
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    await CampaignSchedulerService(db).execute_step(campaign_lead_id)
    row = await db.get(CampaignLead, campaign_lead_id)
    assert row.next_action_at is None  # stalled at draft

    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    send_response = await client.post(f"/api/v1/leads/{lead['id']}/emails/{email.id}/send")
    assert send_response.status_code == 200, send_response.text

    await db.refresh(row)
    assert row.status == "in_progress"
    assert row.current_step_order == 1
    assert row.next_action_at is not None  # advanced to step 2 by the approval-then-send hook


async def test_execute_step_sends_immediately_when_automation_enabled(
    client: AsyncClient, db: AsyncSession
) -> None:
    registration = await register_user(client)
    _campaign, lead, campaign_lead = await _full_send_now_setup(
        client, db, _org_id(registration), requires_approval=False
    )

    await CampaignSchedulerService(db).execute_step(uuid.UUID(campaign_lead["id"]))

    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert email is not None
    assert email.current_status == "sent"

    row = await db.get(CampaignLead, uuid.UUID(campaign_lead["id"]))
    assert row.status == "completed"  # single-step sequence — sending it completes the enrollment
    assert row.completed_at is not None


async def test_ai_personalized_step_generates_and_stalls_for_approval(
    client: AsyncClient, db: AsyncSession, eager_generation
) -> None:
    registration = await register_user(client)
    campaign = await _create_campaign(client, requires_approval=True)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=None, content_source="ai_personalized")
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = uuid.UUID(enrolled.json()["data"]["id"])
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    await CampaignSchedulerService(db).execute_step(campaign_lead_id)

    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert email is not None
    assert email.current_status == "draft"
    assert email.ai_generated is True


async def test_wait_step_advances_without_sending(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    org_id = _org_id(registration)
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    sequence = await _create_sequence(client, campaign["id"])
    await client.post(
        f"/api/v1/sequences/{sequence['id']}/steps", json={"step_type": "wait", "step_order": 1, "delay_days": 3}
    )
    await _create_email_step(client, sequence["id"], step_order=2, template_id=str(template.id), delay_days=0)
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = uuid.UUID(enrolled.json()["data"]["id"])
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    await CampaignSchedulerService(db).execute_step(campaign_lead_id)

    await db.refresh(row)
    assert row.current_step_order == 1
    assert row.status == "in_progress"
    no_email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert no_email is None


# ─── Auto-stop ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("lead_status", "expected_campaign_lead_status"),
    [("unsubscribed", "opted_out"), ("bounced", "bounced"), ("replied", "replied")],
)
async def test_auto_stop_halts_sequence(
    client: AsyncClient, db: AsyncSession, lead_status: str, expected_campaign_lead_status: str
) -> None:
    registration = await register_user(client)
    _campaign, lead, campaign_lead = await _full_send_now_setup(
        client, db, _org_id(registration), requires_approval=True
    )
    lead_row = await db.get(Lead, uuid.UUID(lead["id"]))
    lead_row.status = lead_status
    await db.commit()

    await CampaignSchedulerService(db).execute_step(uuid.UUID(campaign_lead["id"]))

    row = await db.get(CampaignLead, uuid.UUID(campaign_lead["id"]))
    assert row.status == expected_campaign_lead_status
    assert row.next_action_at is None
    assert row.completed_at is not None

    # No email was generated/sent — auto-stop runs before step execution.
    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert email is None


# ─── Conditional skip ─────────────────────────────────────────────────────────────


async def test_conditional_skip_when_already_opened(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    org_id = _org_id(registration)
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client, requires_approval=False)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    await _create_email_step(
        client, sequence["id"], step_order=2, template_id=str(template.id), delay_days=1,
        condition={"skip_if": "opened"},
    )
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = uuid.UUID(enrolled.json()["data"]["id"])
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    # Step 1 sends immediately (full automation).
    await CampaignSchedulerService(db).execute_step(campaign_lead_id)
    email = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    assert email.current_status == "sent"

    # Simulate the lead opening it, then force step 2 due now.
    email.current_status = "opened"
    await db.commit()
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    await CampaignSchedulerService(db).execute_step(campaign_lead_id)

    await db.refresh(row)
    assert row.status == "completed"  # step 2 was skipped, sequence exhausted
    # still exactly one Email — step 2 never generated a second one
    count = await db.scalar(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))
    all_emails = (await db.execute(select(Email).where(Email.lead_id == uuid.UUID(lead["id"])))).scalars().all()
    assert len(all_emails) == 1


# ─── Dashboard ──────────────────────────────────────────────────────────────────


async def test_campaign_dashboard_funnel(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    org_id = _org_id(registration)
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client)
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    lead = await _create_lead(client)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})

    response = await client.get(f"/api/v1/campaigns/{campaign['id']}/dashboard")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["funnel"]["enrolled"] == 1
    assert data["total_enrolled"] == 1


# ─── Permissions + multi-tenancy ──────────────────────────────────────────────────


async def test_multi_tenancy_isolation_on_campaigns(client: AsyncClient) -> None:
    await register_user(client)
    campaign = await _create_campaign(client)

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    cross_tenant = await other_client.get(f"/api/v1/campaigns/{campaign['id']}")
    assert cross_tenant.status_code == 404
    await other_client.aclose()


async def test_sales_role_can_read_but_not_delete_campaign(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    campaign = await _create_campaign(client)
    sales_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="sales")

    read = await sales_client.get(f"/api/v1/campaigns/{campaign['id']}")
    assert read.status_code == 200

    forbidden = await sales_client.delete(f"/api/v1/campaigns/{campaign['id']}")
    assert forbidden.status_code == 403
    await sales_client.aclose()


async def test_viewer_cannot_create_campaign(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    viewer_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="viewer")
    response = await viewer_client.post("/api/v1/campaigns", json={"name": "Nope"})
    assert response.status_code == 403
    await viewer_client.aclose()


# ─── Scheduler concurrency: FOR UPDATE SKIP LOCKED ────────────────────────────────


async def test_scheduler_claim_is_exclusive_under_concurrency(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    org_id = _org_id(registration)
    template = await _create_template(db, org_id)
    campaign = await _create_campaign(client)
    await client.post(f"/api/v1/campaigns/{campaign['id']}/activate")
    sequence = await _create_sequence(client, campaign["id"])
    await _create_email_step(client, sequence["id"], step_order=1, template_id=str(template.id))
    lead = await _create_lead(client)
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    campaign_lead_id = uuid.UUID(enrolled.json()["data"]["id"])
    row = await db.get(CampaignLead, campaign_lead_id)
    row.next_action_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    claims: list[list] = []

    async def _claim_pass(hold_seconds: float) -> None:
        async with session_factory() as session:
            async with session.begin():
                ids = await CampaignLeadRepository(session).claim_due_batch(
                    now=datetime.now(timezone.utc), batch_size=10
                )
                claims.append(ids)
                await asyncio.sleep(hold_seconds)  # keep the transaction (and its lock) open

    try:
        await asyncio.gather(_claim_pass(0.6), _claim_pass(0.1))
    finally:
        await engine.dispose()

    claimed_by = [ids for ids in claims if campaign_lead_id in ids]
    assert len(claimed_by) == 1  # exactly one of the two concurrent passes claimed it
