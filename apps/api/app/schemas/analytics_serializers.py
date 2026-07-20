"""ORM -> response-schema mapping for Reports and Dashboard Widgets."""

from app.models.remaining_domains import DashboardWidget, Report
from app.schemas.analytics import DashboardWidgetResponse, ReportConfigSchema, ReportResponse


def serialize_report(report: Report) -> ReportResponse:
    return ReportResponse(
        id=str(report.id),
        organization_id=str(report.organization_id),
        name=report.name,
        report_type=report.report_type,
        config=ReportConfigSchema(**report.config) if report.config else None,
        is_scheduled=report.is_scheduled,
        schedule_cron=report.schedule_cron,
        recipients=report.recipients,
        last_run_at=report.last_run_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def serialize_dashboard_widget(widget: DashboardWidget) -> DashboardWidgetResponse:
    return DashboardWidgetResponse(
        id=str(widget.id),
        widget_type=widget.widget_type,
        title=widget.title,
        position_x=widget.position_x,
        position_y=widget.position_y,
        width=widget.width,
        height=widget.height,
        config=widget.config,
    )
