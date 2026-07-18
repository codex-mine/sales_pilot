"""
AI -> Company Research.

`trigger_research` never calls an LLM SDK directly — it gathers source
material from the company's own website, then calls
`AIJobService.run_job(...)` (the AI Foundation chokepoint) with
`response_format="json"`, which guarantees the returned AIJob is either
COMPLETED with a parsed `AIOutput.content_json`, or FAILED — malformed model
output never reaches this service as something to silently store.

Finalization (parsing the completed job's output into the `company_research`
row) happens either inline, right after `run_job` returns, when the job is
already terminal (eager/test mode — see AIJobService's `ai_execute_jobs_eagerly`
switch), or via a `research` queue Celery task (`app.workers.research_tasks`)
that polls the job to terminal in production/async mode. Either path ends up
calling `finalize()` exactly once.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions.errors import NotFoundError
from app.models.ai.models import AIJob
from app.models.crm.models import Company
from app.models.enums import AIAgentTypeEnum, AIJobStatusEnum, ActivityTypeEnum, AuditActionEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.ai_job_repository import AIJobRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_research_repository import CompanyResearchRepository
from app.services.ai.ai_job_service import AIJobService

_TERMINAL_STATUSES = {AIJobStatusEnum.COMPLETED, AIJobStatusEnum.FAILED, AIJobStatusEnum.CANCELLED}
_RESEARCH_USER_AGENT = "SalesPilotResearchBot/1.0 (+https://salespilot.app/research-bot)"
_ABOUT_HREF_HINTS = ("/about", "about-us", "/company", "/who-we-are")


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def _find_about_href(soup: BeautifulSoup) -> str | None:
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].lower()
        if any(hint in href for hint in _ABOUT_HREF_HINTS):
            return anchor["href"]
    return None


class CompanyResearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.companies = CompanyRepository(db)
        self.research_repo = CompanyResearchRepository(db)
        self.ai_jobs = AIJobRepository(db)
        self.ai_job_service = AIJobService(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def require_company(self, company_id: uuid.UUID, organization_id: uuid.UUID) -> Company:
        company = await self.companies.get_by_id(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company not found.")
        return company

    def _is_fresh(self, researched_at: datetime) -> bool:
        staleness = timedelta(days=get_settings().research_staleness_days)
        return datetime.now(timezone.utc) - researched_at < staleness

    # ─── Trigger ────────────────────────────────────────────────────────────────

    async def trigger_research(
        self,
        organization_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        actor: User,
        force: bool = False,
        auto_finalize: bool = True,
    ) -> AIJob:
        """`auto_finalize=False` is used by ProspectAnalysisService's lead
        orchestration, which owns waiting for this job and finalizing it
        itself (via `orchestrate_lead_research`) so the job is never
        finalized twice."""
        company = await self.require_company(company_id, organization_id)
        existing = await self.research_repo.get_by_company(company_id, organization_id)
        if (
            existing is not None
            and not force
            and existing.ai_job_id is not None
            and self._is_fresh(existing.researched_at)
        ):
            return await self.ai_job_service.require_job(existing.ai_job_id, organization_id)

        source_text, data_quality = await self._gather_source_material(company)

        await self.activities.record(
            organization_id=organization_id, company_id=company.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.AI_RESEARCH_STARTED,
            summary=f"Company research started by {actor.full_name}",
        )
        await self.db.commit()

        job = await self.ai_job_service.run_job(
            organization_id=organization_id,
            job_type="research_company",
            entity_type="company",
            entity_id=company.id,
            prompt_template_name="research_company",
            variables={
                "company_name": company.name,
                "context": self._build_context(company, source_text, data_quality),
                "data_quality": data_quality,
            },
            agent_type=AIAgentTypeEnum.RESEARCH,
            initiated_by=actor.id,
            response_format="json",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="company_research", resource_id=company.id,
            changes={"event": "company_research_triggered", "ai_job_id": str(job.id), "force": force},
        )
        await self.db.commit()

        if job.status in _TERMINAL_STATUSES:
            job = await self.finalize(job, company, actor)
        elif auto_finalize:
            from app.workers.research_tasks import finalize_company_research

            finalize_company_research.apply_async(
                args=[str(job.id), str(organization_id), str(company.id), str(actor.id)],
                queue="research",
            )
        return job

    def _build_context(self, company: Company, source_text: str, data_quality: str) -> str:
        lines = [
            f"Industry: {company.industry or 'unknown'}",
            f"Size: {company.size_range or 'unknown'} ({company.employee_count or 'unknown'} employees)",
            f"Existing description on file: {company.description or 'none'}",
            f"LinkedIn: {company.linkedin_url or 'none on file'}",
        ]
        if data_quality == "llm_knowledge_only":
            lines.append(
                "No website content could be retrieved for this company — rely on "
                "your own knowledge and clearly flag any uncertainty rather than "
                "inventing specifics."
            )
        else:
            lines.append(f"Website content (homepage/about page):\n{source_text}")
        return "\n".join(lines)

    # ─── Finalize ───────────────────────────────────────────────────────────────

    async def finalize(self, job: AIJob, company: Company, actor: User) -> AIJob:
        if job.status != AIJobStatusEnum.COMPLETED:
            await self.audit_log.record(
                organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
                action=AuditActionEnum.UPDATE, resource_type="company_research", resource_id=company.id,
                changes={
                    "event": "company_research_failed",
                    "ai_job_id": str(job.id),
                    "error": job.error_message,
                },
            )
            await self.db.commit()
            return job

        output = job.outputs[-1] if job.outputs else None
        parsed: dict[str, Any] = dict(output.content_json) if output and output.content_json else {}
        data_quality = (job.input_data or {}).get("variables", {}).get("data_quality", "web_enriched")

        await self.research_repo.upsert(
            company_id=company.id,
            organization_id=company.organization_id,
            ai_job_id=job.id,
            summary=parsed.get("summary"),
            products_services=parsed.get("products_services"),
            target_customers=parsed.get("target_customers"),
            business_model=parsed.get("business_model"),
            technologies=parsed.get("technologies"),
            competitors=parsed.get("competitors"),
            recent_news=parsed.get("recent_news"),
            pain_points=parsed.get("pain_points"),
            sales_opportunities=parsed.get("sales_opportunities"),
            estimated_revenue=parsed.get("estimated_revenue"),
            funding_stage=parsed.get("funding_stage"),
            growth_signals=parsed.get("growth_signals"),
            raw_research={**parsed, "data_quality": data_quality},
        )

        # Denormalized Company fields: only fill gaps, never overwrite
        # user-entered data with AI output.
        company_updates: dict[str, Any] = {}
        if not company.description and parsed.get("summary"):
            company_updates["description"] = parsed["summary"]
        technologies = parsed.get("technologies")
        if not company.technologies and isinstance(technologies, list) and technologies:
            company_updates["technologies"] = [str(t) for t in technologies][:50]
        if company_updates:
            await self.companies.update(company, company_updates, updated_by=actor.id)

        await self.activities.record(
            organization_id=company.organization_id, company_id=company.id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.AI_RESEARCH_COMPLETED,
            summary=f"Company research completed for {company.name}",
        )
        await self.audit_log.record(
            organization_id=company.organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="company_research", resource_id=company.id,
            changes={"event": "company_research_completed", "ai_job_id": str(job.id)},
        )
        await self.db.commit()
        return job

    # ─── Source material gathering ───────────────────────────────────────────────
    # Swap this single method for a real enrichment provider (Clearbit,
    # Apollo, ...) later — everything above only depends on the
    # (text, data_quality) tuple it returns.

    async def _gather_source_material(self, company: Company) -> tuple[str, str]:
        if not company.website:
            return "", "llm_knowledge_only"

        settings = get_settings()
        url = company.website if "//" in company.website else f"https://{company.website}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.research_website_fetch_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": _RESEARCH_USER_AGENT},
            ) as client:
                if not await self._is_fetch_allowed(client, url):
                    return "", "llm_knowledge_only"

                response = await client.get(url)
                response.raise_for_status()
                content = response.content[: settings.research_website_max_bytes]
                soup = BeautifulSoup(content, "html.parser")
                pages = [_extract_text(soup)]

                about_href = _find_about_href(soup)
                if about_href:
                    about_url = urljoin(str(response.url), about_href)
                    try:
                        about_response = await client.get(about_url)
                        about_response.raise_for_status()
                        about_soup = BeautifulSoup(
                            about_response.content[: settings.research_website_max_bytes], "html.parser"
                        )
                        pages.append(_extract_text(about_soup))
                    except httpx.HTTPError:
                        pass
        except (httpx.HTTPError, httpx.InvalidURL):
            return "", "llm_knowledge_only"

        text = "\n\n".join(page for page in pages if page).strip()
        if not text:
            return "", "llm_knowledge_only"
        return text[: settings.research_website_max_bytes], "web_enriched"

    async def _is_fetch_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        robots_url = urljoin(url, "/robots.txt")
        parser = RobotFileParser()
        try:
            response = await client.get(robots_url)
            if response.status_code >= 400:
                return True  # no robots.txt on this host -> allowed by default
            parser.parse(response.text.splitlines())
        except httpx.HTTPError:
            return True
        return parser.can_fetch(_RESEARCH_USER_AGENT, url)
