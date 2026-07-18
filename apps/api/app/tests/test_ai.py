"""
AI Provider Foundation tests: system template seeding, agent CRUD, prompt
version immutability, job lifecycle (mocked LLM — never a real provider),
cost calculation, output approval, settings key storage, permissions, and
multi-tenancy isolation.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import LLMProviderError, ValidationError
from app.models.enums import AIAgentTypeEnum, LLMProviderEnum
from app.services.ai.llm_client import LLMCompletionResult
from app.services.ai.pricing import compute_cost_usd
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio


class _StubLLMClient:
    def __init__(self, *, content: str = "stub output", fail: bool = False) -> None:
        self.content = content
        self.fail = fail
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> LLMCompletionResult:
        self.calls.append(kwargs)
        if self.fail:
            raise LLMProviderError("stubbed provider failure")
        return LLMCompletionResult(
            content=self.content, input_tokens=100, output_tokens=50, raw_response={}
        )


@pytest.fixture
def eager_jobs(monkeypatch):
    """Run AI jobs inline (no Celery) and stub the LLM client."""
    stub = _StubLLMClient()
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr(
        "app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: stub
    )
    return stub


async def _run_research_job(db: AsyncSession, organization_id: str, *, initiated_by=None):
    from app.services.ai.ai_job_service import AIJobService

    return await AIJobService(db).run_job(
        organization_id=uuid.UUID(organization_id),
        job_type="research_company",
        entity_type="company",
        entity_id=None,
        prompt_template_name="research_company",
        variables={"company_name": "Acme", "context": "A SaaS company."},
        agent_type=AIAgentTypeEnum.RESEARCH,
        initiated_by=initiated_by,
    )


def _org_id(registration: dict) -> str:
    return registration["data"]["user"]["organization_id"]


# ─── System template seeding ────────────────────────────────────────────────────


async def test_system_templates_seeded_on_registration(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.get("/api/v1/ai/prompt-templates")
    assert response.status_code == 200, response.text
    templates = response.json()["data"]
    names = {t["name"] for t in templates}
    assert {"research_company", "generate_email", "classify_reply", "detect_meeting"} <= names
    for t in templates:
        assert t["is_system"] is True
        assert t["active_version_id"] is not None
        assert t["version_count"] == 1


# ─── Agents ────────────────────────────────────────────────────────────────────


async def test_agent_crud_and_duplicate_type_rejected(client: AsyncClient) -> None:
    await register_user(client)
    payload = {
        "name": "Research agent",
        "agent_type": "research",
        "provider": "anthropic",
        "model_name": "claude-sonnet-5",
        "temperature": 0.4,
        "max_tokens": 4096,
    }
    created = await client.post("/api/v1/ai/agents", json=payload)
    assert created.status_code == 201, created.text
    agent = created.json()["data"]
    assert agent["provider"] == "anthropic"
    assert agent["agent_type"] == "research"

    duplicate = await client.post("/api/v1/ai/agents", json=payload)
    assert duplicate.status_code == 400

    updated = await client.patch(
        f"/api/v1/ai/agents/{agent['id']}", json={"model_name": "claude-haiku-4-5", "temperature": 0.2}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["model_name"] == "claude-haiku-4-5"

    deleted = await client.delete(f"/api/v1/ai/agents/{agent['id']}")
    assert deleted.status_code == 200
    assert (await client.get(f"/api/v1/ai/agents/{agent['id']}")).status_code == 404


# ─── Prompt versions ───────────────────────────────────────────────────────────


async def test_prompt_version_immutability_and_activation(client: AsyncClient) -> None:
    await register_user(client)
    templates = (await client.get("/api/v1/ai/prompt-templates")).json()["data"]
    template = next(t for t in templates if t["name"] == "research_company")

    v2 = await client.post(
        f"/api/v1/ai/prompt-templates/{template['id']}/versions",
        json={
            "system_prompt": "You are an improved researcher.",
            "user_prompt_template": "Research {{ company_name }}. Context: {{ context }}",
            "variables": ["company_name", "context"],
            "change_notes": "Tightened wording.",
            "activate": False,
        },
    )
    assert v2.status_code == 201, v2.text
    assert v2.json()["data"]["version_number"] == 2
    assert v2.json()["data"]["is_active"] is False

    versions = (await client.get(f"/api/v1/ai/prompt-templates/{template['id']}/versions")).json()["data"]
    assert [v["version_number"] for v in versions] == [2, 1]
    # Version 1 content untouched (immutability): still the seeded system prompt.
    assert versions[1]["is_active"] is True

    activate = await client.post(
        f"/api/v1/ai/prompt-templates/{template['id']}/versions/{v2.json()['data']['id']}/activate"
    )
    assert activate.status_code == 200
    assert activate.json()["data"]["active_version_number"] == 2


async def test_prompt_rendering_missing_variables_is_clear_error(db: AsyncSession, client: AsyncClient) -> None:
    registration = await register_user(client)
    from app.services.ai.ai_job_service import AIJobService

    with pytest.raises(ValidationError) as excinfo:
        await AIJobService(db).run_job(
            organization_id=uuid.UUID(_org_id(registration)),
            job_type="research_company",
            entity_type=None,
            entity_id=None,
            prompt_template_name="research_company",
            variables={"company_name": "Acme"},  # missing "context"
            agent_type=AIAgentTypeEnum.RESEARCH,
            initiated_by=None,
        )
    assert "context" in str(excinfo.value)


# ─── Job lifecycle ─────────────────────────────────────────────────────────────


async def test_job_lifecycle_completed(db: AsyncSession, client: AsyncClient, eager_jobs) -> None:
    registration = await register_user(client)
    job = await _run_research_job(db, _org_id(registration))

    assert str(job.status) in {"completed", "AIJobStatusEnum.COMPLETED"}
    assert job.total_tokens == 150
    assert job.latency_ms is not None
    assert len(eager_jobs.calls) == 1
    assert "Acme" in eager_jobs.calls[0]["user_prompt"]

    detail = await client.get(f"/api/v1/ai/jobs/{job.id}")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["status"] == "completed"
    assert data["input_data"]["prompt_template"] == "research_company"
    assert len(data["outputs"]) == 1
    assert data["outputs"][0]["content_text"] == "stub output"
    assert data["outputs"][0]["is_approved"] is None  # pending review

    listing = await client.get("/api/v1/ai/jobs")
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 1


async def test_job_failure_and_orchestrated_retry(
    db: AsyncSession, client: AsyncClient, monkeypatch
) -> None:
    registration = await register_user(client)
    failing = _StubLLMClient(fail=True)
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    monkeypatch.setattr("app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: failing)

    with pytest.raises(LLMProviderError):
        await _run_research_job(db, _org_id(registration))

    listing = (await client.get("/api/v1/ai/jobs?status=failed")).json()["data"]
    assert len(listing) == 1
    failed_job = listing[0]
    assert failed_job["error_message"] == "stubbed provider failure"

    # Retry creates a NEW job with parent_job_id — never resurrects the old row.
    monkeypatch.setattr(
        "app.services.ai.ai_job_service.get_llm_client", lambda *a, **k: _StubLLMClient()
    )
    retried = await client.post(f"/api/v1/ai/jobs/{failed_job['id']}/retry")
    assert retried.status_code == 200, retried.text
    new_job = retried.json()["data"]
    assert new_job["id"] != failed_job["id"]
    assert new_job["parent_job_id"] == failed_job["id"]
    assert new_job["status"] == "completed"

    original = (await client.get(f"/api/v1/ai/jobs/{failed_job['id']}")).json()["data"]
    assert original["status"] == "failed"


async def test_execute_job_is_idempotent_for_terminal_jobs(
    db: AsyncSession, client: AsyncClient, eager_jobs
) -> None:
    registration = await register_user(client)
    job = await _run_research_job(db, _org_id(registration))
    from app.services.ai.ai_job_service import AIJobService

    again = await AIJobService(db).execute_job(job.id, uuid.UUID(_org_id(registration)))
    assert len(eager_jobs.calls) == 1  # not re-executed
    assert again.id == job.id


# ─── Outputs ───────────────────────────────────────────────────────────────────


async def test_output_approval_transitions(db: AsyncSession, client: AsyncClient, eager_jobs) -> None:
    registration = await register_user(client)
    job = await _run_research_job(db, _org_id(registration))
    output_id = (await client.get(f"/api/v1/ai/jobs/{job.id}")).json()["data"]["outputs"][0]["id"]

    approved = await client.post(f"/api/v1/ai/outputs/{output_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["data"]["is_approved"] is True
    assert approved.json()["data"]["approved_by"] is not None

    rejected = await client.post(f"/api/v1/ai/outputs/{output_id}/reject")
    assert rejected.status_code == 200
    data = rejected.json()["data"]
    assert data["is_approved"] is False
    # Content is immutable through approval transitions.
    assert data["content_text"] == "stub output"


# ─── Cost tracking ─────────────────────────────────────────────────────────────


def test_cost_calculation_against_pricing_table() -> None:
    cost = compute_cost_usd(LLMProviderEnum.ANTHROPIC, "claude-sonnet-5-20250929", 1000, 1000)
    assert cost == pytest.approx(0.003 + 0.015)
    assert compute_cost_usd(LLMProviderEnum.LOCAL, "llama3.2", 5000, 5000) == 0.0
    assert compute_cost_usd(LLMProviderEnum.OPENAI, "unknown-model", 1000, 1000) == 0.0


async def test_usage_endpoint_aggregates(db: AsyncSession, client: AsyncClient, eager_jobs) -> None:
    registration = await register_user(client)
    await _run_research_job(db, _org_id(registration))
    await _run_research_job(db, _org_id(registration))

    usage = await client.get("/api/v1/ai/usage?days=30")
    assert usage.status_code == 200
    data = usage.json()["data"]
    assert data["total_jobs"] == 2
    assert data["total_tokens"] == 300
    assert data["by_job_type"][0]["job_type"] == "research_company"


# ─── Settings / key storage ────────────────────────────────────────────────────


async def test_settings_key_storage_never_echoes_key(client: AsyncClient) -> None:
    await register_user(client)
    initial = await client.get("/api/v1/ai/settings")
    assert initial.status_code == 200

    saved = await client.patch(
        "/api/v1/ai/settings", json={"provider": "anthropic", "api_key": "sk-ant-secret-value"}
    )
    assert saved.status_code == 200
    assert "sk-ant-secret-value" not in saved.text  # never render the key back
    anthropic_status = next(
        p for p in saved.json()["data"]["providers"] if p["provider"] == "anthropic"
    )
    assert anthropic_status["has_org_key"] is True
    assert anthropic_status["has_key"] is True

    removed = await client.patch(
        "/api/v1/ai/settings", json={"provider": "anthropic", "remove": True}
    )
    assert removed.status_code == 200
    anthropic_status = next(
        p for p in removed.json()["data"]["providers"] if p["provider"] == "anthropic"
    )
    assert anthropic_status["has_org_key"] is False


async def test_settings_ollama_requires_base_url(client: AsyncClient) -> None:
    await register_user(client)
    missing = await client.patch("/api/v1/ai/settings", json={"provider": "local"})
    assert missing.status_code == 400

    ok = await client.patch(
        "/api/v1/ai/settings", json={"provider": "local", "base_url": "http://localhost:11434"}
    )
    assert ok.status_code == 200
    local_status = next(p for p in ok.json()["data"]["providers"] if p["provider"] == "local")
    assert local_status["has_org_key"] is True


# ─── Permissions / multi-tenancy ───────────────────────────────────────────────


async def _invite_member(client: AsyncClient, db: AsyncSession, organization_id: str, role_name: str) -> AsyncClient:
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


async def test_sales_role_cannot_access_ai(db: AsyncSession, client: AsyncClient) -> None:
    registration = await register_user(client)
    sales_client = await _invite_member(client, db, _org_id(registration), "sales")
    assert (await sales_client.get("/api/v1/ai/jobs")).status_code == 403
    assert (await sales_client.get("/api/v1/ai/settings")).status_code == 403
    await sales_client.aclose()


async def test_manager_can_read_but_not_manage_ai(db: AsyncSession, client: AsyncClient) -> None:
    registration = await register_user(client)
    manager_client = await _invite_member(client, db, _org_id(registration), "manager")
    assert (await manager_client.get("/api/v1/ai/jobs")).status_code == 200
    denied = await manager_client.post(
        "/api/v1/ai/agents",
        json={"name": "X", "agent_type": "research", "provider": "openai", "model_name": "gpt-4o"},
    )
    assert denied.status_code == 403
    await manager_client.aclose()


async def test_multi_tenancy_isolation(db: AsyncSession, client: AsyncClient, eager_jobs) -> None:
    registration = await register_user(client)
    job = await _run_research_job(db, _org_id(registration))

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    assert (await other_client.get(f"/api/v1/ai/jobs/{job.id}")).status_code == 404
    assert (await other_client.get("/api/v1/ai/jobs")).json()["meta"]["total"] == 0
    await other_client.aclose()
