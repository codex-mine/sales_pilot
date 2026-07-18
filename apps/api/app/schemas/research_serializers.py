"""ORM -> response-schema mapping for the Company Research / Prospect
Analysis module."""

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.models.ai.models import CompanyResearch, ProspectAnalysis
from app.schemas.research import CompanyResearchResponse, ProspectAnalysisResponse


def _is_stale(researched_at: datetime) -> bool:
    staleness = timedelta(days=get_settings().research_staleness_days)
    return datetime.now(timezone.utc) - researched_at >= staleness


def serialize_company_research(research: CompanyResearch) -> CompanyResearchResponse:
    raw = research.raw_research or {}
    return CompanyResearchResponse(
        id=str(research.id),
        company_id=str(research.company_id),
        ai_job_id=str(research.ai_job_id) if research.ai_job_id else None,
        summary=research.summary,
        products_services=research.products_services,
        target_customers=research.target_customers,
        business_model=research.business_model,
        technologies=research.technologies,
        competitors=research.competitors,
        recent_news=research.recent_news,
        pain_points=research.pain_points,
        sales_opportunities=research.sales_opportunities,
        estimated_revenue=research.estimated_revenue,
        funding_stage=research.funding_stage,
        growth_signals=research.growth_signals,
        data_quality=raw.get("data_quality", "web_enriched"),
        researched_at=research.researched_at,
        is_stale=_is_stale(research.researched_at),
    )


def serialize_prospect_analysis(analysis: ProspectAnalysis) -> ProspectAnalysisResponse:
    return ProspectAnalysisResponse(
        id=str(analysis.id),
        lead_id=str(analysis.lead_id),
        ai_job_id=str(analysis.ai_job_id) if analysis.ai_job_id else None,
        buying_intent=analysis.buying_intent,
        priority_score=analysis.priority_score,
        recommended_approach=analysis.recommended_approach,
        value_proposition=analysis.value_proposition,
        predicted_objections=analysis.predicted_objections,
        likely_goals=analysis.likely_goals,
        decision_authority=analysis.decision_authority,
        best_contact_time=analysis.best_contact_time,
        analysed_at=analysis.analysed_at,
    )
