"""
Analytics -> saved/custom Reports. CRUD follows `campaign_service.py`'s
pattern (AuditLog per mutation, soft delete); Activity doesn't apply since
Reports aren't lead/company-scoped.

`run()` computes the report's data by delegating to `DashboardService`'s
per-widget methods (never re-implementing the pipeline/campaign/AI/email
queries here — see that module's docstring for the Metric-first reasoning),
renders a plain HTML table, and — when recipients are set — delivers it via
the existing transactional `email_service.send_email` (the same SMTP path
auth emails use), never the outreach sender client from module 07, since a
report is a transactional notification to the requesting org, not cold
outreach.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError
from app.models.enums import AuditActionEnum
from app.models.identity.models import User
from app.models.remaining_domains import Report
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.analytics import CreateReportRequest, ReportConfigSchema, UpdateReportRequest
from app.services import email_service
from app.services.analytics.dashboard_service import DashboardService


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.reports = ReportRepository(db)
        self.audit_log = AuditLogRepository(db)
        self.dashboard = DashboardService(db)

    async def require_report(self, report_id: uuid.UUID, organization_id: uuid.UUID) -> Report:
        report = await self.reports.get_by_id(report_id, organization_id)
        if report is None:
            raise NotFoundError("Report not found.")
        return report

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, page: int = 1, page_size: int = 25
    ) -> tuple[list[Report], int]:
        return await self.reports.list_for_organization(organization_id, page=page, page_size=page_size)

    async def create(self, organization_id: uuid.UUID, *, payload: CreateReportRequest, actor: User) -> Report:
        fields: dict[str, Any] = payload.model_dump(exclude={"config", "recipients"})
        fields["config"] = payload.config.model_dump()
        fields["recipients"] = [str(r) for r in payload.recipients] if payload.recipients else None
        report = await self.reports.create(organization_id=organization_id, created_by=actor.id, **fields)
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="report", resource_id=report.id,
            changes={"event": "report_created", "report_type": payload.report_type},
        )
        await self.db.commit()
        return await self.require_report(report.id, organization_id)

    async def update(self, report: Report, *, payload: UpdateReportRequest, actor: User) -> Report:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True, exclude={"config", "recipients"})
        if payload.config is not None:
            changes["config"] = payload.config.model_dump()
        if "recipients" in payload.model_fields_set:
            changes["recipients"] = [str(r) for r in payload.recipients] if payload.recipients else None
        if not changes:
            return report
        report = await self.reports.update(report, changes, updated_by=actor.id)
        await self.audit_log.record(
            organization_id=report.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="report", resource_id=report.id,
            changes={"event": "report_updated"},
        )
        await self.db.commit()
        # Re-fetch: `updated_at`'s `onupdate=func.now()` is server-computed,
        # so the in-memory value is stale until an awaited re-read — matches
        # `campaign_service.update()`'s same re-fetch-after-commit pattern.
        return await self.require_report(report.id, report.organization_id)

    async def delete(self, report: Report, *, actor: User) -> None:
        await self.audit_log.record(
            organization_id=report.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.DELETE, resource_type="report", resource_id=report.id,
            changes={"event": "report_deleted"},
        )
        await self.reports.soft_delete(report)
        await self.db.commit()

    # ─── Run / deliver ──────────────────────────────────────────────────────────

    async def run(self, report: Report, *, actor: User) -> tuple[Report, int, list[str]]:
        """Computes the report's data, emails it to `report.recipients` (if
        any), stamps `last_run_at`, and audit-logs the run. Returns
        (report, row_count, delivered_to) for the API response."""
        html, text, row_count = await self._render(report)

        delivered_to: list[str] = []
        for recipient in report.recipients or []:
            await email_service.send_email(to=recipient, subject=f"SalesPilot report: {report.name}", html_body=html, text_body=text)
            delivered_to.append(recipient)

        report = await self.reports.record_run(report)
        await self.audit_log.record(
            organization_id=report.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="report", resource_id=report.id,
            changes={"event": "report_run", "row_count": row_count, "delivered_to": delivered_to},
        )
        await self.db.commit()
        report = await self.require_report(report.id, report.organization_id)
        return report, row_count, delivered_to

    async def _render(self, report: Report) -> tuple[str, str, int]:
        config = ReportConfigSchema(**(report.config or {}))
        rows: list[dict[str, Any]]

        if report.report_type == "pipeline":
            funnel = await self.dashboard.get_pipeline_funnel(report.organization_id)
            rows = [{"Status": status, "Count": count} for status, count in funnel.counts.items()]
        elif report.report_type == "campaign_performance":
            perf = await self.dashboard.get_campaign_performance(report.organization_id, limit=1000)
            rows = [
                {
                    "Campaign": item.campaign_name, "Status": item.status, "Enrolled": item.enrolled_count,
                    "Replied": item.replied_count, "Meetings booked": item.meeting_booked_count,
                    "Reply rate": f"{item.reply_rate}%",
                }
                for item in perf.campaigns
            ]
        elif report.report_type == "ai_usage":
            usage = await self.dashboard.get_ai_usage(report.organization_id)
            rows = [
                {"Job type": item.job_type, "Jobs": item.job_count, "Tokens": item.total_tokens, "Cost (USD)": item.cost_usd}
                for item in usage.by_job_type
            ]
        else:  # "email_performance"
            perf = await self.dashboard.get_email_performance(report.organization_id)
            rows = [
                {"Metric": "Open rate", "Value": f"{perf.open_rate}%"},
                {"Metric": "Click rate", "Value": f"{perf.click_rate}%"},
                {"Metric": "Bounce rate", "Value": f"{perf.bounce_rate}%"},
            ]

        html = _render_html_table(report.name, config.date_range, rows)
        text = _render_text_table(report.name, config.date_range, rows)
        return html, text, len(rows)


def _render_html_table(report_name: str, date_range: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"<h2>{report_name}</h2><p>No data for this report ({date_range}).</p>"
    headers = list(rows[0].keys())
    header_html = "".join(f"<th style='text-align:left;padding:6px 12px;border-bottom:1px solid #ddd'>{h}</th>" for h in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{row.get(h, '')}</td>" for h in headers) + "</tr>"
        for row in rows
    )
    return (
        f"<h2>{report_name}</h2><p style='color:#666'>Range: {date_range}</p>"
        f"<table style='border-collapse:collapse;width:100%'><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"
    )


def _render_text_table(report_name: str, date_range: str, rows: list[dict[str, Any]]) -> str:
    lines = [report_name, f"Range: {date_range}", ""]
    for row in rows:
        lines.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines) if rows else f"{report_name}\nNo data for this report ({date_range})."
