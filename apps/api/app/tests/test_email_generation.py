"""
AI Personalized Email Generation & Human Review tests: end-to-end generation
(single call returning multiple variants), auto-triggered research when
missing, regeneration with feedback/prior-content, approval (with and
without edits), save-as-template, bulk fan-out, permissions, and
multi-tenancy.

The website fetch and the LLM client are always mocked here — this suite
never hits a real network or a real LLM provider.
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import AIOutputParsingError
from app.models.crm.models import Lead
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.user_repository import UserRepository
from app.tests.ai_fakes import FakeChatModel
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio

_RESEARCH_JSON = {
    "summary": "Acme Corp builds analytical engines for enterprise data teams.",
    "products_services": ["Analytical Engine Platform"],
    "target_customers": "Mid-market data teams",
    "business_model": "B2B SaaS",
    "technologies": ["Python", "Postgres"],
    "competitors": ["Babbage Systems"],
    "recent_news": ["Raised a Series B round"],
    "pain_points": ["Manual data reconciliation eats analyst time"],
    "sales_opportunities": ["Automate reconciliation workflows"],
    "estimated_revenue": "$10M-$50M",
    "funding_stage": "series_b",
    "growth_signals": ["Hiring 20 engineers this quarter"],
}

_PROSPECT_JSON = {
    "buying_intent": "high",
    "priority_score": 82,
    "recommended_approach": "Lead with ROI on reconciliation time saved.",
    "value_proposition": "Cut reconciliation time by 80%.",
    "predicted_objections": ["Budget constraints this quarter"],
    "likely_goals": ["Reduce operational overhead"],
    "decision_authority": "decision_maker",
    "best_contact_time": "Tuesday mornings",
}

_EMAIL_VARIANTS_JSON = [
    {
        "subject": "Cutting reconciliation time at Acme Corp",
        "body_html": "<p>Hi Grace, saw Acme is scaling fast — reconciliation shouldn't be the bottleneck.</p>",
        "body_text": "Hi Grace, saw Acme is scaling fast — reconciliation shouldn't be the bottleneck.",
        "reasoning": "Leads with a specific pain point and recent growth signal.",
    },
    {
        "subject": "Quick question about Acme's data reconciliation",
        "body_html": "<p>Hi Grace, quick one — how is your team handling manual reconciliation today?</p>",
        "body_text": "Hi Grace, quick one — how is your team handling manual reconciliation today?",
        "reasoning": "Question-based opener to drive a reply.",
    },
]


def _generation_responder(malformed: bool = False):
    """Branches on the system prompt's distinguishing phrase to serve
    research / prospect-analysis / email-generation / self-critique
    responses from one stub, since generate_email's auto-research-trigger
    chains through all three earlier job types in a single test run, and
    email_agent's `self_critique` node (module 13) makes a second call per
    generation for its own "no generic filler" review — this always reports
    "passes" so these pre-existing tests exercise exactly one regeneration
    pass (zero), matching their original single-call assumption; the
    dedicated self-critique regeneration behavior itself is covered in
    test_email_agent_graph.py."""

    def _respond(system_prompt: str, _user_prompt: str) -> str:
        if "strict editor" in system_prompt:
            return json.dumps({"passes": True, "feedback": None})
        if "sales development representative" in system_prompt:
            return "not json{{{" if malformed else json.dumps(_EMAIL_VARIANTS_JSON)
        if "sales strategist" in system_prompt:
            return json.dumps(_PROSPECT_JSON)
        return json.dumps(_RESEARCH_JSON)

    return _respond


@pytest.fixture
def eager_generation(monkeypatch):
    stub = FakeChatModel(responder=_generation_responder())
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)
    return stub


@pytest.fixture(autouse=True)
def mock_website_fetch(monkeypatch):
    async def _fake(self, company):
        if not company.website:
            return "", "llm_knowledge_only"
        return "Acme Corp homepage: we build analytical engines.", "web_enriched"

    monkeypatch.setattr(
        "app.services.ai.company_research_service.CompanyResearchService._gather_source_material", _fake
    )
    return _fake


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


async def _create_company(client: AsyncClient, **overrides) -> dict:
    payload = {"name": "Acme Corp", "website": "https://www.acme.example.com", "industry": "SaaS", **overrides}
    response = await client.post("/api/v1/companies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_lead(client: AsyncClient, **overrides) -> dict:
    payload = {
        "first_name": "Grace", "last_name": "Hopper", "email": unique_email("lead"),
        "job_title": "VP Engineering", "company_name": "Acme Corp", **overrides,
    }
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _link_lead_to_company(db: AsyncSession, lead_id: str, company_id: str) -> None:
    lead = await db.get(Lead, uuid.UUID(lead_id))
    lead.company_id = uuid.UUID(company_id)
    await db.commit()


async def _research_lead(client: AsyncClient, db: AsyncSession, lead_id: str, company_id: str | None) -> None:
    """Fully researches a lead (company research + prospect analysis) so
    email generation has grounded context — mirrors the Research module's
    own orchestration, driven through the same public endpoint."""
    if company_id:
        await _link_lead_to_company(db, lead_id, company_id)
    triggered = await client.post(f"/api/v1/leads/{lead_id}/research")
    assert triggered.status_code == 200, triggered.text


async def _invite_and_accept(client: AsyncClient, db: AsyncSession, *, organization_id: str, role_name: str) -> AsyncClient:
    from sqlalchemy import select

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


# ─── Generation end-to-end ───────────────────────────────────────────────────────


async def test_generate_email_end_to_end_multi_variant(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])
    calls_before = len(eager_generation.calls)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 2},
    )
    assert response.status_code == 200, response.text
    job = response.json()["data"]
    assert job["status"] == "completed"
    assert job["job_type"] == "generate_email"
    # Two LLM calls for this generate request (context already had research
    # from before): generate_variants, then self_critique's review pass
    # (module 13's email_agent graph — see _generation_responder above).
    assert len(eager_generation.calls) == calls_before + 2

    # Re-fetch fresh: the raw chokepoint output (output_type="generate_email",
    # holding the untouched parsed array) plus the 2 per-variant AIOutput rows
    # finalize() split it into (output_type="email_variant", each individually
    # approvable) — 3 rows total on this one job.
    job_detail = (await client.get(f"/api/v1/ai/jobs/{job['id']}")).json()["data"]
    assert len(job_detail["outputs"]) == 3
    raw_output = next(o for o in job_detail["outputs"] if o["output_type"] == "generate_email")
    assert raw_output["content_json"] == _EMAIL_VARIANTS_JSON
    variant_outputs = [o for o in job_detail["outputs"] if o["output_type"] == "email_variant"]
    assert len(variant_outputs) == 2
    assert {o["content_json"]["subject"] for o in variant_outputs} == {v["subject"] for v in _EMAIL_VARIANTS_JSON}
    assert all(o["is_approved"] is None for o in variant_outputs)


async def test_generate_email_auto_triggers_research_when_missing(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _link_lead_to_company(db, lead["id"], company["id"])

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "professional", "variant_count": 2},
    )
    assert response.status_code == 200, response.text

    # Research was auto-triggered and completed (eager mode) before the email call.
    research = await client.get(f"/api/v1/companies/{company['id']}/research")
    assert research.json()["data"] is not None
    analysis = await client.get(f"/api/v1/leads/{lead['id']}/prospect-analysis")
    assert analysis.json()["data"] is not None


async def test_malformed_email_json_fails_ai_job_cleanly(
    db: AsyncSession, client: AsyncClient, monkeypatch
) -> None:
    registration = await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])

    stub = FakeChatModel(responder=_generation_responder(malformed=True))
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)

    from app.services.ai.email_generation_service import EmailGenerationService
    from app.models.enums import EmailTemplateTypeEnum, EmailToneEnum

    actor = await UserRepository(db).get_by_id(uuid.UUID(registration["data"]["id"]))
    with pytest.raises(AIOutputParsingError):
        await EmailGenerationService(db).generate_email(
            uuid.UUID(_org_id(registration)), uuid.UUID(lead["id"]), actor=actor,
            template_type=EmailTemplateTypeEnum.COLD_OUTREACH, tone=EmailToneEnum.FRIENDLY,
        )

    jobs, total = await AIJobRepository(db).list_for_organization(
        uuid.UUID(_org_id(registration)), job_type=["generate_email"]
    )
    assert total == 1
    assert jobs[0].status == "failed"

    drafts = await client.get(f"/api/v1/leads/{lead['id']}/emails/drafts")
    assert drafts.json()["data"] == []


# ─── Regeneration ───────────────────────────────────────────────────────────────


async def test_regenerate_incorporates_feedback_and_marks_prior_rejected(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])

    first = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    first_job = first.json()["data"]
    first_output_id = first_job["outputs"][0]["id"]
    # That raw output isn't the approvable variant — fetch the variant AIOutput via drafts-adjacent job listing.
    job_detail = (await client.get(f"/api/v1/ai/jobs/{first_job['id']}")).json()["data"]
    assert job_detail["outputs"][0]["is_approved"] is None

    # Find the actual per-variant AIOutput created by finalize() via the job history.
    from sqlalchemy import select

    from app.models.ai.models import AIOutput

    variant_output = await db.scalar(
        select(AIOutput).where(AIOutput.job_id == uuid.UUID(first_job["id"]), AIOutput.output_type == "email_variant")
    )
    assert variant_output is not None
    assert variant_output.is_approved is None

    regenerated = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/regenerate",
        json={
            "source_output_id": str(variant_output.id),
            "custom_instruction": "make it shorter and more casual",
            "variant_count": 1,
        },
    )
    assert regenerated.status_code == 200, regenerated.text

    await db.refresh(variant_output)
    assert variant_output.is_approved is False  # marked rejected by the regenerate call

    # calls[-1] is self_critique's review pass (module 13's email_agent
    # graph runs it after every generation) — the generation call itself,
    # with the regenerate-specific context, is the one before it.
    generation_call = eager_generation.calls[-2]
    assert "make it shorter and more casual" in generation_call["user_prompt"]
    assert "previous draft was rejected" in generation_call["user_prompt"].lower()


# ─── Approval ───────────────────────────────────────────────────────────────────


async def test_approve_variant_creates_draft_email_with_personalization_data(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])

    generated = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    job_id = generated.json()["data"]["id"]

    from sqlalchemy import select

    from app.models.ai.models import AIOutput

    variant = await db.scalar(
        select(AIOutput).where(AIOutput.job_id == uuid.UUID(job_id), AIOutput.output_type == "email_variant")
    )
    assert variant is not None

    approved = await client.post(
        f"/api/v1/ai/outputs/{variant.id}/approve-email",
        json={"from_email": "sales@salespilot.app", "from_name": "SalesPilot Team"},
    )
    assert approved.status_code == 200, approved.text
    email = approved.json()["data"]
    assert email["current_status"] == "draft"
    assert email["ai_generated"] is True
    assert email["subject"] == _EMAIL_VARIANTS_JSON[0]["subject"]
    assert email["personalization_data"]["ai_output_id"] == str(variant.id)

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "email_generated"

    await db.refresh(variant)
    assert variant.is_approved is True
    assert variant.content_json == _EMAIL_VARIANTS_JSON[0]  # untouched original


async def test_approve_with_edits_preserves_original_ai_output(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])

    generated = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    job_id = generated.json()["data"]["id"]

    from sqlalchemy import select

    from app.models.ai.models import AIOutput

    variant = await db.scalar(
        select(AIOutput).where(AIOutput.job_id == uuid.UUID(job_id), AIOutput.output_type == "email_variant")
    )

    edited_subject = "A hand-edited subject line"
    approved = await client.post(
        f"/api/v1/ai/outputs/{variant.id}/approve-email",
        json={
            "from_email": "sales@salespilot.app",
            "edited_subject": edited_subject,
            "save_as_template": True,
            "template_name": "My Reusable Template",
        },
    )
    assert approved.status_code == 200, approved.text
    email = approved.json()["data"]
    assert email["subject"] == edited_subject

    await db.refresh(variant)
    assert variant.content_json["subject"] == _EMAIL_VARIANTS_JSON[0]["subject"]  # unchanged

    templates = await client.get("/api/v1/email-templates")
    assert templates.status_code == 200
    saved = next(t for t in templates.json()["data"] if t["name"] == "My Reusable Template")
    assert saved["subject"] == edited_subject
    assert saved["is_ai_generated"] is True


async def test_reject_variant_does_not_create_email(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])

    generated = await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    job_id = generated.json()["data"]["id"]

    from sqlalchemy import select

    from app.models.ai.models import AIOutput

    variant = await db.scalar(
        select(AIOutput).where(AIOutput.job_id == uuid.UUID(job_id), AIOutput.output_type == "email_variant")
    )

    rejected = await client.post(f"/api/v1/ai/outputs/{variant.id}/reject-email")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["is_approved"] is False

    drafts = await client.get(f"/api/v1/leads/{lead['id']}/emails/drafts")
    assert drafts.json()["data"] == []


# ─── Bulk generation ─────────────────────────────────────────────────────────────


async def test_bulk_generate_emails_queues_without_blocking(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    lead_ids = [(await _create_lead(client, email=unique_email("bulk")))["id"] for _ in range(3)]

    import app.workers.email_tasks as email_tasks

    calls: list[tuple] = []
    monkeypatch.setattr(
        email_tasks.dispatch_lead_email_generation, "apply_async",
        lambda args, queue: calls.append((args, queue)),
    )

    response = await client.post(
        "/api/v1/leads/bulk/generate-emails",
        json={"lead_ids": lead_ids, "template_type": "cold_outreach", "tone": "professional"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["queued_count"] == 3
    assert len(calls) == 3
    assert all(queue == "email" for _args, queue in calls)


# ─── Permissions / multi-tenancy ────────────────────────────────────────────────


async def test_viewer_cannot_generate_but_can_read_drafts(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    registration = await register_user(client)
    lead = await _create_lead(client)
    viewer_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="viewer"
    )
    denied = await viewer_client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly"},
    )
    assert denied.status_code == 403
    allowed = await viewer_client.get(f"/api/v1/leads/{lead['id']}/emails/drafts")
    assert allowed.status_code == 200
    await viewer_client.aclose()


async def test_sales_role_can_generate_but_not_manage_templates(
    db: AsyncSession, client: AsyncClient, eager_generation
) -> None:
    registration = await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])
    sales_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="sales"
    )
    generated = await sales_client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )
    assert generated.status_code == 200, generated.text

    templates = await sales_client.get("/api/v1/email-templates")
    assert templates.status_code == 200  # campaigns.read
    if templates.json()["data"]:
        template_id = templates.json()["data"][0]["id"]
        denied = await sales_client.patch(f"/api/v1/email-templates/{template_id}", json={"name": "x"})
        assert denied.status_code == 403  # no campaigns.update
    await sales_client.aclose()


async def test_multi_tenancy_isolation_on_email_drafts(
    client: AsyncClient, db: AsyncSession, eager_generation
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _research_lead(client, db, lead["id"], company["id"])
    await client.post(
        f"/api/v1/leads/{lead['id']}/emails/generate",
        json={"template_type": "cold_outreach", "tone": "friendly", "variant_count": 1},
    )

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    isolated = await other_client.get(f"/api/v1/leads/{lead['id']}/emails/drafts")
    assert isolated.status_code == 404
    await other_client.aclose()
