"""Request/response schemas for AI Company Research & Prospect Analysis
(Companies -> Research tab, Leads -> Research tab). Trigger endpoints return
`AIJobResponse` (app.schemas.ai) directly so the frontend can hand the id
straight to the existing `useAIJob` poller — no separate job shape here."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai import AIJobResponse

BUYING_INTENT_CHOICES = ["high", "medium", "low"]
DECISION_AUTHORITY_CHOICES = ["decision_maker", "influencer", "evaluator", "end_user"]
DATA_QUALITY_CHOICES = ["web_enriched", "llm_knowledge_only"]


class CompanyResearchResponse(BaseModel):
    id: str
    company_id: str
    ai_job_id: str | None
    summary: str | None
    products_services: list | None
    target_customers: str | None
    business_model: str | None
    technologies: list | None
    competitors: list | None
    recent_news: list | None
    pain_points: list | None
    sales_opportunities: list | None
    estimated_revenue: str | None
    funding_stage: str | None
    growth_signals: list | None
    data_quality: str
    researched_at: datetime
    is_stale: bool


class ProspectAnalysisResponse(BaseModel):
    id: str
    lead_id: str
    ai_job_id: str | None
    buying_intent: str | None
    priority_score: float | None
    recommended_approach: str | None
    value_proposition: str | None
    predicted_objections: list | None
    likely_goals: list | None
    decision_authority: str | None
    best_contact_time: str | None
    analysed_at: datetime


class LeadResearchStatusResponse(BaseModel):
    """Composite status for the Lead -> Research tab: the lead's own
    research-pipeline status plus whichever company-research / prospect-
    analysis AIJob is currently the latest for this lead. `prospect_job` is
    intentionally nullable even mid-flight — in async/production mode the
    prospect-analysis job doesn't exist yet until company research (if
    triggered) finishes; the frontend keeps polling this endpoint until it
    appears."""

    lead_id: str
    lead_status: str
    company_job: AIJobResponse | None
    prospect_job: AIJobResponse | None


class BulkLeadResearchRequest(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=200)


class BulkResearchResponse(BaseModel):
    requested_count: int
    queued_count: int
    errors: list[str]
