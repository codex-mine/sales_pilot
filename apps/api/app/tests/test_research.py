"""
AI Company Research & Prospect Analysis tests: company research end-to-end,
prospect analysis (with and without existing company research), the
orchestrated "research this lead" parent/child job chain, staleness
skip/force, malformed-JSON failure handling, bulk fan-out, permissions, and
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
from app.services.ai.llm_client import LLMCompletionResult
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


class _StubResearchLLMClient:
    """Returns canned JSON keyed by which system prompt is in play — the
    research_company and analyze_prospect system prompts are distinct
    enough ("sales research analyst" vs "sales strategist") to branch on."""

    def __init__(self, *, fail: bool = False, malformed: bool = False) -> None:
        self.fail = fail
        self.malformed = malformed
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> LLMCompletionResult:
        self.calls.append(kwargs)
        if self.fail:
            from app.exceptions.errors import LLMProviderError

            raise LLMProviderError("stubbed provider failure")
        if self.malformed:
            return LLMCompletionResult(content="not json{{{", input_tokens=10, output_tokens=5, raw_response={})
        system_prompt = kwargs.get("system_prompt", "")
        content = json.dumps(_PROSPECT_JSON if "sales strategist" in system_prompt else _RESEARCH_JSON)
        return LLMCompletionResult(content=content, input_tokens=120, output_tokens=80, raw_response={})


@pytest.fixture
def eager_research(monkeypatch):
    """Eager AI jobs (no Celery) + a stub LLM client returning canned
    structured JSON for both research_company and analyze_prospect."""
    stub = _StubResearchLLMClient()
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: stub)
    return stub


@pytest.fixture(autouse=True)
def mock_website_fetch(monkeypatch):
    """Never hit a real network: canned "web_enriched" source material for
    every company that has a website configured."""

    async def _fake(self, company):
        if not company.website:
            return "", "llm_knowledge_only"
        return "Acme Corp homepage: we build analytical engines. About: founded 1830.", "web_enriched"

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
    """No public API links an existing Lead to a Company by id (leads only
    carry a denormalized `company_name`) — set the FK directly for tests
    that need the orchestrated company-then-prospect chain."""
    lead = await db.get(Lead, uuid.UUID(lead_id))
    lead.company_id = uuid.UUID(company_id)
    await db.commit()


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


# ─── Company research end-to-end ─────────────────────────────────────────────────


async def test_company_research_end_to_end(client: AsyncClient, eager_research) -> None:
    await register_user(client)
    company = await _create_company(client)

    trigger = await client.post(f"/api/v1/companies/{company['id']}/research")
    assert trigger.status_code == 200, trigger.text
    job = trigger.json()["data"]
    assert job["status"] == "completed"
    assert job["job_type"] == "research_company"

    fetched = await client.get(f"/api/v1/companies/{company['id']}/research")
    assert fetched.status_code == 200
    research = fetched.json()["data"]
    assert research is not None
    assert research["summary"] == _RESEARCH_JSON["summary"]
    assert research["pain_points"] == _RESEARCH_JSON["pain_points"]
    assert research["data_quality"] == "web_enriched"
    assert research["is_stale"] is False
    assert research["ai_job_id"] == job["id"]

    history = await client.get(f"/api/v1/companies/{company['id']}/research/history")
    assert history.status_code == 200
    assert history.json()["meta"]["total"] == 1


async def test_company_research_no_website_flags_llm_knowledge_only(
    client: AsyncClient, eager_research
) -> None:
    await register_user(client)
    company = await _create_company(client, website=None)

    trigger = await client.post(f"/api/v1/companies/{company['id']}/research")
    assert trigger.status_code == 200, trigger.text

    research = (await client.get(f"/api/v1/companies/{company['id']}/research")).json()["data"]
    assert research["data_quality"] == "llm_knowledge_only"


async def test_company_research_staleness_skips_unless_forced(
    client: AsyncClient, eager_research
) -> None:
    await register_user(client)
    company = await _create_company(client)

    first = await client.post(f"/api/v1/companies/{company['id']}/research")
    first_job_id = first.json()["data"]["id"]
    assert len(eager_research.calls) == 1

    again = await client.post(f"/api/v1/companies/{company['id']}/research")
    assert again.json()["data"]["id"] == first_job_id
    assert len(eager_research.calls) == 1  # no new LLM call — freshness short-circuited it

    forced = await client.post(f"/api/v1/companies/{company['id']}/research?force=true")
    assert forced.json()["data"]["id"] != first_job_id
    assert len(eager_research.calls) == 2


async def test_malformed_json_fails_ai_job_cleanly(db: AsyncSession, client: AsyncClient, monkeypatch) -> None:
    registration = await register_user(client)
    company = await _create_company(client)
    stub = _StubResearchLLMClient(malformed=True)
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: stub)

    from app.services.ai.company_research_service import CompanyResearchService

    actor = await UserRepository(db).get_by_id(uuid.UUID(registration["data"]["id"]))
    with pytest.raises(AIOutputParsingError):
        await CompanyResearchService(db).trigger_research(
            uuid.UUID(_org_id(registration)), uuid.UUID(company["id"]), actor=actor
        )

    # The job landed FAILED, and no garbage was ever written to company_research.
    jobs, total = await AIJobRepository(db).list_for_organization(
        uuid.UUID(_org_id(registration)), job_type=["research_company"]
    )
    assert total == 1
    assert jobs[0].status == "failed"
    assert "malformed" in (jobs[0].error_message or "").lower()

    fetched = await client.get(f"/api/v1/companies/{company['id']}/research")
    assert fetched.json()["data"] is None


# ─── Prospect analysis ──────────────────────────────────────────────────────────


async def test_prospect_analysis_without_company_research(client: AsyncClient, eager_research) -> None:
    await register_user(client)
    lead = await _create_lead(client)  # no linked company

    trigger = await client.post(f"/api/v1/leads/{lead['id']}/research")
    assert trigger.status_code == 200, trigger.text
    status_data = trigger.json()["data"]
    assert status_data["company_job"] is None
    assert status_data["prospect_job"]["status"] == "completed"
    assert "no company research summary" in "".join(
        c.get("user_prompt", "") for c in eager_research.calls
    ).lower() or "no company research available" in "".join(
        c.get("user_prompt", "") for c in eager_research.calls
    ).lower()

    analysis = (await client.get(f"/api/v1/leads/{lead['id']}/prospect-analysis")).json()["data"]
    assert analysis["buying_intent"] == "high"
    assert analysis["predicted_objections"] == _PROSPECT_JSON["predicted_objections"]

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "research_done"


async def test_orchestrated_lead_research_chains_company_then_prospect(
    db: AsyncSession, client: AsyncClient, eager_research
) -> None:
    await register_user(client)
    company = await _create_company(client)
    lead = await _create_lead(client)
    await _link_lead_to_company(db, lead["id"], company["id"])

    trigger = await client.post(f"/api/v1/leads/{lead['id']}/research")
    assert trigger.status_code == 200, trigger.text
    data = trigger.json()["data"]
    assert data["company_job"]["status"] == "completed"
    assert data["prospect_job"]["status"] == "completed"
    assert data["prospect_job"]["parent_job_id"] == data["company_job"]["id"]

    company_research = (await client.get(f"/api/v1/companies/{company['id']}/research")).json()["data"]
    assert company_research["summary"] == _RESEARCH_JSON["summary"]

    analysis = (await client.get(f"/api/v1/leads/{lead['id']}/prospect-analysis")).json()["data"]
    assert analysis["buying_intent"] == "high"

    lead_after = (await client.get(f"/api/v1/leads/{lead['id']}")).json()["data"]
    assert lead_after["status"] == "research_done"


# ─── Bulk research ──────────────────────────────────────────────────────────────


async def test_bulk_research_queues_without_blocking(client: AsyncClient, monkeypatch) -> None:
    """Default (non-eager) settings: the bulk endpoint must return fast by
    fanning out a Celery dispatch per lead instead of running research
    inline in the request."""
    await register_user(client)
    lead_ids = [(await _create_lead(client, email=unique_email("bulk")))["id"] for _ in range(3)]

    import app.workers.research_tasks as research_tasks

    calls: list[tuple] = []
    monkeypatch.setattr(
        research_tasks.dispatch_lead_research, "apply_async",
        lambda args, queue: calls.append((args, queue)),
    )

    response = await client.post("/api/v1/leads/bulk/research", json={"lead_ids": lead_ids})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["requested_count"] == 3
    assert data["queued_count"] == 3
    assert len(calls) == 3
    assert all(queue == "research" for _args, queue in calls)


async def test_bulk_research_reports_missing_lead_ids(client: AsyncClient) -> None:
    await register_user(client)
    lead = await _create_lead(client)
    missing_id = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/leads/bulk/research", json={"lead_ids": [lead["id"], missing_id]}
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["queued_count"] == 1
    assert any(missing_id in err for err in data["errors"])


# ─── Permissions / multi-tenancy ────────────────────────────────────────────────


async def test_viewer_cannot_trigger_research_but_can_read(
    db: AsyncSession, client: AsyncClient, eager_research
) -> None:
    registration = await register_user(client)
    company = await _create_company(client)
    viewer_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="viewer"
    )
    denied = await viewer_client.post(f"/api/v1/companies/{company['id']}/research")
    assert denied.status_code == 403
    allowed = await viewer_client.get(f"/api/v1/companies/{company['id']}/research")
    assert allowed.status_code == 200
    await viewer_client.aclose()


async def test_sales_role_can_trigger_research(db: AsyncSession, client: AsyncClient, eager_research) -> None:
    registration = await register_user(client)
    company = await _create_company(client)
    sales_client = await _invite_and_accept(
        client, db, organization_id=_org_id(registration), role_name="sales"
    )
    triggered = await sales_client.post(f"/api/v1/companies/{company['id']}/research")
    assert triggered.status_code == 200, triggered.text
    await sales_client.aclose()


async def test_multi_tenancy_isolation_on_research(client: AsyncClient, eager_research) -> None:
    await register_user(client)
    company = await _create_company(client)
    await client.post(f"/api/v1/companies/{company['id']}/research")

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    isolated = await other_client.get(f"/api/v1/companies/{company['id']}/research")
    assert isolated.status_code == 404
    await other_client.aclose()
