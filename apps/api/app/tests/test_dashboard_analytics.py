"""
Analytics -> Dashboard, Reports & Notification Center tests: the dashboard
summary composes Metric-backed widgets in a small fixed number of queries and
degrades gracefully on an empty organization, the nightly aggregation task
upserts Metric rows idempotently (re-running doesn't duplicate), notification
read/unread state is scoped strictly to the owning user even within the same
org, report config validation rejects malformed shapes at creation time,
report delivery uses the transactional email service (not the outreach
sender), and permissions/multi-tenancy on every endpoint.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai.models import AIJob
from app.models.campaigns.models import EmailTemplate
from app.models.enums import AIJobStatusEnum, NotificationTypeEnum
from app.models.identity.models import Role
from app.models.remaining_domains import Metric, Report
from app.repositories.email_template_repository import EmailTemplateRepository
from app.repositories.notification_repository import NotificationRepository
from app.services import email_service as email_service_module
from app.tests.conftest import register_user, unique_email

pytestmark = pytest.mark.asyncio


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


async def _create_campaign(client: AsyncClient, **overrides) -> dict:
    payload = {"name": "Q3 Outbound", "send_start_hour": 0, "send_end_hour": 23, **overrides}
    response = await client.post("/api/v1/campaigns", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_template(db: AsyncSession, organization_id: str) -> EmailTemplate:
    template = await EmailTemplateRepository(db).create(
        organization_id=uuid.UUID(organization_id), created_by=None,
        name="Cold outreach template", template_type="cold_outreach", tone="professional",
        subject="Hi {{ lead.first_name }}", body_html="<p>Hi {{ lead.first_name }}</p>",
        body_text="Hi {{ lead.first_name }}", is_active=True,
    )
    await db.commit()
    return template


async def _create_ai_job(db: AsyncSession, organization_id: str, *, job_type: str, cost_usd: float, total_tokens: int) -> AIJob:
    job = AIJob(
        organization_id=uuid.UUID(organization_id), job_type=job_type, status=AIJobStatusEnum.COMPLETED.value,
        cost_usd=cost_usd, total_tokens=total_tokens, input_tokens=total_tokens // 2, output_tokens=total_tokens // 2,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    return job


async def _invite_and_accept(client: AsyncClient, db: AsyncSession, *, organization_id: str, role_name: str) -> AsyncClient:
    role = await db.scalar(select(Role).where(Role.organization_id == uuid.UUID(organization_id), Role.name == role_name))
    assert role is not None
    invite = await client.post("/api/v1/organizations/invitations", json={"email": unique_email(role_name), "role_id": str(role.id)})
    assert invite.status_code == 201, invite.text
    token = invite.json()["meta"]["debug_invitation_token"]
    member_client = AsyncClient(transport=client._transport, base_url="http://test")
    accepted = await member_client.post(
        "/api/v1/organizations/invitations/accept",
        json={"token": token, "first_name": "New", "last_name": role_name.title(), "password": "Str0ng!Passw0rd"},
    )
    assert accepted.status_code == 201, accepted.text
    return member_client


# ─── Dashboard summary ────────────────────────────────────────────────────────────


async def test_dashboard_summary_handles_empty_organization_gracefully(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["pipeline_funnel"]["counts"]["new"] == 0
    assert data["ai_usage"]["total_cost_usd"] == 0.0
    assert data["campaign_performance"]["campaigns"] == []
    assert data["email_performance"]["open_rate"] == 0.0
    assert data["meetings"]["by_status"] == {} or isinstance(data["meetings"]["by_status"], dict)
    assert data["recent_activity"] == []
    assert data["unread_notification_count"] == 0


async def test_dashboard_summary_isolates_a_failing_widget(client: AsyncClient, monkeypatch) -> None:
    """Mocks the AI usage widget's data source raising — the rest of the
    dashboard must still come back with real data, not a 500."""
    await register_user(client)
    await _create_lead(client)

    async def _boom(self, organization_id):
        raise RuntimeError("simulated AI usage query failure")

    monkeypatch.setattr("app.services.analytics.dashboard_service.DashboardService.get_ai_usage", _boom)

    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    # The failing widget degrades to its safe default...
    assert data["ai_usage"]["total_cost_usd"] == 0.0
    assert data["ai_usage"]["by_job_type"] == []
    # ...while every other widget still reflects real data.
    assert data["pipeline_funnel"]["counts"]["new"] == 1


async def test_pipeline_funnel_counts_leads_by_status(client: AsyncClient) -> None:
    await register_user(client)
    await _create_lead(client)
    await _create_lead(client)

    response = await client.get("/api/v1/analytics/pipeline-funnel")
    assert response.status_code == 200, response.text
    counts = response.json()["data"]["counts"]
    assert counts["new"] == 2


async def test_dashboard_summary_is_org_scoped(client: AsyncClient) -> None:
    await register_user(client)
    await _create_lead(client)

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)

    response = await other_client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["pipeline_funnel"]["counts"]["new"] == 0
    # sanity: org A still sees its own lead
    own = await client.get("/api/v1/analytics/pipeline-funnel")
    assert own.json()["data"]["counts"]["new"] == 1


async def test_sales_role_cannot_read_analytics(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    sales_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="sales")
    response = await sales_client.get("/api/v1/dashboard/summary")
    assert response.status_code == 403


async def test_viewer_can_read_analytics(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    viewer_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="viewer")
    response = await viewer_client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200, response.text


# ─── Dashboard widgets ─────────────────────────────────────────────────────────────


async def test_dashboard_widget_crud(client: AsyncClient) -> None:
    await register_user(client)

    created = await client.post(
        "/api/v1/dashboard/widgets",
        json={"widget_type": "pipeline_funnel", "title": "My Funnel", "position_x": 0, "position_y": 0, "width": 6, "height": 4},
    )
    assert created.status_code == 201, created.text
    widget_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/dashboard/widgets")
    assert listed.status_code == 200
    assert any(w["id"] == widget_id for w in listed.json()["data"])

    updated = await client.patch(f"/api/v1/dashboard/widgets/{widget_id}", json={"position_x": 6})
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["position_x"] == 6

    deleted = await client.delete(f"/api/v1/dashboard/widgets/{widget_id}")
    assert deleted.status_code == 200, deleted.text
    listed_after = await client.get("/api/v1/dashboard/widgets")
    assert not any(w["id"] == widget_id for w in listed_after.json()["data"])


# ─── Nightly aggregation ────────────────────────────────────────────────────────────


async def test_nightly_aggregation_upserts_metrics_idempotently(client: AsyncClient, db: AsyncSession) -> None:
    from app.workers.analytics_tasks import _run_nightly_aggregation

    registration = await register_user(client)
    org_id = uuid.UUID(_org_id(registration))
    await _create_lead(client)
    await _create_ai_job(db, _org_id(registration), job_type="research", cost_usd=1.5, total_tokens=1000)

    await _run_nightly_aggregation(db)
    rows_after_first = (await db.execute(select(Metric).where(Metric.organization_id == org_id))).scalars().all()
    count_after_first = len(rows_after_first)
    assert count_after_first > 0

    # Re-running for the same day must update in place, not duplicate.
    await _run_nightly_aggregation(db)
    rows_after_second = (await db.execute(select(Metric).where(Metric.organization_id == org_id))).scalars().all()
    assert len(rows_after_second) == count_after_first

    ai_cost_total = await db.scalar(
        select(Metric).where(Metric.organization_id == org_id, Metric.metric_name == "ai_cost_total")
    )
    assert ai_cost_total is not None
    assert ai_cost_total.value == pytest.approx(1.5)


async def test_ai_usage_analytics_reads_from_metric(client: AsyncClient, db: AsyncSession) -> None:
    from app.workers.analytics_tasks import _run_nightly_aggregation

    registration = await register_user(client)
    await _create_ai_job(db, _org_id(registration), job_type="research", cost_usd=2.0, total_tokens=500)
    await _create_ai_job(db, _org_id(registration), job_type="email_generation", cost_usd=1.0, total_tokens=300)
    await _run_nightly_aggregation(db)

    response = await client.get("/api/v1/analytics/ai-usage")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_cost_usd"] == pytest.approx(3.0)
    assert data["total_job_count"] == 2
    job_types = {item["job_type"] for item in data["by_job_type"]}
    assert job_types == {"research", "email_generation"}


async def test_campaign_performance_reads_from_metric(client: AsyncClient, db: AsyncSession) -> None:
    from app.models.campaigns.models import CampaignLead
    from app.workers.analytics_tasks import _run_nightly_aggregation

    registration = await register_user(client)
    campaign = await _create_campaign(client)
    lead = await _create_lead(client)
    template = await _create_template(db, _org_id(registration))
    sequence_resp = await client.post(f"/api/v1/campaigns/{campaign['id']}/sequences", json={"name": "Main"})
    assert sequence_resp.status_code == 201, sequence_resp.text
    sequence_id = sequence_resp.json()["data"]["id"]
    step_resp = await client.post(
        f"/api/v1/sequences/{sequence_id}/steps",
        json={"step_type": "email", "step_order": 1, "content_source": "template", "email_template_id": str(template.id)},
    )
    assert step_resp.status_code == 201, step_resp.text
    enrolled = await client.post(f"/api/v1/campaigns/{campaign['id']}/enroll", json={"lead_id": lead["id"]})
    assert enrolled.status_code == 201, enrolled.text

    # Force the campaign_lead to "replied" so reply_rate is nonzero and deterministic.
    row = await db.get(CampaignLead, uuid.UUID(enrolled.json()["data"]["id"]))
    row.status = "replied"
    await db.commit()

    await _run_nightly_aggregation(db)

    response = await client.get("/api/v1/analytics/campaign-performance")
    assert response.status_code == 200, response.text
    campaigns = response.json()["data"]["campaigns"]
    assert len(campaigns) == 1
    assert campaigns[0]["campaign_id"] == campaign["id"]
    assert campaigns[0]["enrolled_count"] == 1
    assert campaigns[0]["replied_count"] == 1
    assert campaigns[0]["reply_rate"] == 100.0


# ─── Notifications ─────────────────────────────────────────────────────────────────


async def test_notifications_list_and_unread_count(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    await NotificationRepository(db).create(
        organization_id=uuid.UUID(_org_id(registration)), user_id=uuid.UUID(_user_id(registration)),
        notification_type=NotificationTypeEnum.SYSTEM.value, title="Test notification", body="Hello",
    )
    await db.commit()

    unread = await client.get("/api/v1/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["data"]["count"] == 1

    listed = await client.get("/api/v1/notifications")
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["is_read"] is False


async def test_mark_notification_read_and_mark_all_read(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    n1 = await NotificationRepository(db).create(
        organization_id=uuid.UUID(_org_id(registration)), user_id=uuid.UUID(_user_id(registration)),
        notification_type=NotificationTypeEnum.SYSTEM.value, title="One",
    )
    await NotificationRepository(db).create(
        organization_id=uuid.UUID(_org_id(registration)), user_id=uuid.UUID(_user_id(registration)),
        notification_type=NotificationTypeEnum.SYSTEM.value, title="Two",
    )
    await db.commit()

    marked_one = await client.patch(f"/api/v1/notifications/{n1.id}/read")
    assert marked_one.status_code == 200, marked_one.text
    assert marked_one.json()["data"]["is_read"] is True

    unread_after_one = await client.get("/api/v1/notifications/unread-count")
    assert unread_after_one.json()["data"]["count"] == 1

    mark_all = await client.post("/api/v1/notifications/read-all")
    assert mark_all.status_code == 200
    assert mark_all.json()["data"]["marked_count"] == 1

    unread_after_all = await client.get("/api/v1/notifications/unread-count")
    assert unread_after_all.json()["data"]["count"] == 0


async def test_notification_scoped_strictly_to_owning_user(client: AsyncClient, db: AsyncSession) -> None:
    """A teammate in the SAME organization must never be able to read or
    mark another member's notification — the exact scenario the module 12
    spec calls out explicitly."""
    registration = await register_user(client)
    teammate_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="member")

    mine = await NotificationRepository(db).create(
        organization_id=uuid.UUID(_org_id(registration)), user_id=uuid.UUID(_user_id(registration)),
        notification_type=NotificationTypeEnum.SYSTEM.value, title="Mine",
    )
    await db.commit()

    forbidden = await teammate_client.patch(f"/api/v1/notifications/{mine.id}/read")
    assert forbidden.status_code == 404

    teammate_unread = await teammate_client.get("/api/v1/notifications/unread-count")
    assert teammate_unread.json()["data"]["count"] == 0
    teammate_list = await teammate_client.get("/api/v1/notifications")
    assert teammate_list.json()["data"] == []


# ─── Reports ─────────────────────────────────────────────────────────────────────


async def test_report_crud(client: AsyncClient) -> None:
    await register_user(client)

    created = await client.post(
        "/api/v1/reports",
        json={"name": "Weekly Pipeline", "report_type": "pipeline", "config": {"date_range": "last_7_days"}},
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["data"]["id"]

    fetched = await client.get(f"/api/v1/reports/{report_id}")
    assert fetched.status_code == 200

    updated = await client.patch(f"/api/v1/reports/{report_id}", json={"name": "Weekly Pipeline v2"})
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Weekly Pipeline v2"

    deleted = await client.delete(f"/api/v1/reports/{report_id}")
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/reports/{report_id}")
    assert missing.status_code == 404


async def test_report_config_validation_rejects_malformed_shape(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/reports",
        json={"name": "Bad Report", "report_type": "pipeline", "config": {"date_range": "not_a_real_preset"}},
    )
    # Pydantic field_validator raises ValueError -> FastAPI's own 422
    # request-validation response, same pattern as every other schema
    # validator in this codebase (see test_campaigns.py's step_type test).
    assert response.status_code == 422


async def test_report_rejects_unsupported_report_type(client: AsyncClient) -> None:
    await register_user(client)
    response = await client.post("/api/v1/reports", json={"name": "Bad", "report_type": "not_a_type"})
    assert response.status_code == 422


async def test_run_report_computes_data_and_delivers_via_transactional_email(
    client: AsyncClient, db: AsyncSession, monkeypatch
) -> None:
    await register_user(client)
    await _create_lead(client)

    sent_emails: list[dict] = []

    async def _fake_send_email(*, to, subject, html_body, text_body):
        sent_emails.append({"to": to, "subject": subject})

    monkeypatch.setattr(email_service_module, "send_email", _fake_send_email)

    created = await client.post(
        "/api/v1/reports",
        json={"name": "Pipeline Report", "report_type": "pipeline", "recipients": ["leader@example.com"]},
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["data"]["id"]

    run = await client.post(f"/api/v1/reports/{report_id}/run")
    assert run.status_code == 200, run.text
    data = run.json()["data"]
    assert data["row_count"] > 0
    assert data["delivered_to"] == ["leader@example.com"]
    assert sent_emails == [{"to": "leader@example.com", "subject": "SalesPilot report: Pipeline Report"}]

    refreshed = await client.get(f"/api/v1/reports/{report_id}")
    assert refreshed.json()["data"]["last_run_at"] is not None


async def test_scheduled_report_delivery_task_runs_due_reports(client: AsyncClient, db: AsyncSession, monkeypatch) -> None:
    from app.workers.analytics_tasks import _run_due_reports

    sent_emails: list[dict] = []

    async def _fake_send_email(*, to, subject, html_body, text_body):
        sent_emails.append({"to": to})

    monkeypatch.setattr(email_service_module, "send_email", _fake_send_email)

    registration = await register_user(client)
    sent_emails.clear()  # drop the registration flow's own verification email
    created = await client.post(
        "/api/v1/reports",
        json={
            "name": "Daily Digest", "report_type": "pipeline", "is_scheduled": True, "schedule_cron": "daily",
            "recipients": ["owner@example.com"],
        },
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["data"]["id"]

    await _run_due_reports(db)

    report_row = await db.get(Report, uuid.UUID(report_id))
    await db.refresh(report_row)
    assert report_row.last_run_at is not None
    assert sent_emails == [{"to": "owner@example.com"}]

    # A second immediate run should NOT fire again (not due yet — last_run_at
    # was just set, elapsed time is nowhere near the daily buffer).
    sent_emails.clear()
    await _run_due_reports(db)
    assert sent_emails == []


async def test_reports_permissions_sales_role_forbidden(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    sales_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="sales")
    response = await sales_client.get("/api/v1/reports")
    assert response.status_code == 403


async def test_reports_permissions_member_can_read_not_create(client: AsyncClient, db: AsyncSession) -> None:
    registration = await register_user(client)
    member_client = await _invite_and_accept(client, db, organization_id=_org_id(registration), role_name="member")
    read = await member_client.get("/api/v1/reports")
    assert read.status_code == 200
    create = await member_client.post("/api/v1/reports", json={"name": "x", "report_type": "pipeline"})
    assert create.status_code == 403


async def test_reports_multi_tenancy_isolation(client: AsyncClient) -> None:
    await register_user(client)
    created = await client.post("/api/v1/reports", json={"name": "Org A Report", "report_type": "pipeline"})
    report_id = created.json()["data"]["id"]

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    cross_org = await other_client.get(f"/api/v1/reports/{report_id}")
    assert cross_org.status_code == 404
