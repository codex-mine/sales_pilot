"""Campaigns -> Lead enrollment (individual, bulk, and by saved filter)."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import NotFoundError, ValidationError
from app.models.campaigns.models import Campaign, CampaignLead, Sequence
from app.models.enums import ActivityTypeEnum, AuditActionEnum, CampaignLeadStatusEnum
from app.models.identity.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.campaign_lead_repository import CampaignLeadRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.sequence_repository import SequenceRepository
from app.schemas.campaigns import BulkEnrollResponse, EnrollByFilterRequest
from app.services.campaigns.send_window import roll_forward_into_window


class EnrollmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.sequences = SequenceRepository(db)
        self.campaign_leads = CampaignLeadRepository(db)
        self.leads = LeadRepository(db)
        self.activities = ActivityRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def _resolve_sequence(
        self, campaign: Campaign, sequence_id: uuid.UUID | None
    ) -> Sequence:
        if sequence_id is not None:
            sequence = await self.sequences.get_by_id(sequence_id, campaign.organization_id)
            if sequence is None or sequence.campaign_id != campaign.id:
                raise NotFoundError("Sequence not found on this campaign.")
        else:
            sequence = await self.sequences.get_first_active(campaign.id, campaign.organization_id)
        if sequence is None:
            raise ValidationError("This campaign has no active sequence to enroll into.")
        active_steps = sorted((s for s in sequence.steps if s.is_active), key=lambda s: s.step_order)
        if not active_steps:
            raise ValidationError("This campaign's sequence has no steps yet.")
        return sequence

    def _first_step_run_at(self, campaign: Campaign, sequence: Sequence) -> tuple[uuid.UUID, datetime]:
        first_step = min((s for s in sequence.steps if s.is_active), key=lambda s: s.step_order)
        candidate = datetime.now(timezone.utc) + timedelta(days=first_step.delay_days, hours=first_step.delay_hours)
        run_at = roll_forward_into_window(
            candidate, send_days=campaign.send_days, send_start_hour=campaign.send_start_hour,
            send_end_hour=campaign.send_end_hour, tz_name=campaign.timezone,
        )
        return first_step.id, run_at

    async def enroll_lead(
        self, organization_id: uuid.UUID, campaign_id: uuid.UUID, lead_id: uuid.UUID,
        *, sequence_id: uuid.UUID | None = None, actor: User,
    ) -> CampaignLead:
        campaign = await self.campaigns.get_by_id(campaign_id, organization_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        lead = await self.leads.get_by_id(lead_id, organization_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        if await self.campaign_leads.get_by_campaign_and_lead(campaign_id, lead_id) is not None:
            raise ValidationError(
                "This lead is already enrolled in this campaign.", errors={"lead_id": ["Already enrolled."]}
            )

        sequence = await self._resolve_sequence(campaign, sequence_id)
        next_step_id, next_action_at = self._first_step_run_at(campaign, sequence)

        campaign_lead = await self.campaign_leads.create(
            campaign_id=campaign_id, lead_id=lead_id, organization_id=organization_id,
            sequence_id=sequence.id, status=CampaignLeadStatusEnum.ENROLLED.value,
            current_step_order=0, next_step_id=next_step_id, next_action_at=next_action_at,
        )
        await self.activities.record(
            organization_id=organization_id, lead_id=lead_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.BULK_ACTION,
            summary=f"Enrolled in campaign '{campaign.name}' by {actor.full_name}",
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="campaign_lead", resource_id=campaign_lead.id,
            changes={"event": "lead_enrolled", "campaign_id": str(campaign_id), "lead_id": str(lead_id)},
        )
        await self.db.commit()
        result = await self.campaign_leads.get_by_id(campaign_lead.id, organization_id)
        assert result is not None
        return result

    async def enroll_bulk(
        self, organization_id: uuid.UUID, campaign_id: uuid.UUID, lead_ids: list[uuid.UUID],
        *, sequence_id: uuid.UUID | None = None, actor: User,
    ) -> BulkEnrollResponse:
        campaign = await self.campaigns.get_by_id(campaign_id, organization_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        sequence = await self._resolve_sequence(campaign, sequence_id)
        next_step_id, next_action_at = self._first_step_run_at(campaign, sequence)

        leads = await self.leads.get_many_by_ids(lead_ids, organization_id)
        found_ids = {lead.id for lead in leads}
        errors = [f"{lid}: lead not found in this organization." for lid in lead_ids if lid not in found_ids]

        enrolled = 0
        skipped = 0
        enrolled_ids: list[uuid.UUID] = []
        for lead in leads:
            if await self.campaign_leads.get_by_campaign_and_lead(campaign_id, lead.id) is not None:
                skipped += 1
                continue
            await self.campaign_leads.create(
                campaign_id=campaign_id, lead_id=lead.id, organization_id=organization_id,
                sequence_id=sequence.id, status=CampaignLeadStatusEnum.ENROLLED.value,
                current_step_order=0, next_step_id=next_step_id, next_action_at=next_action_at,
            )
            enrolled_ids.append(lead.id)
            enrolled += 1

        for lead_id in enrolled_ids:
            await self.activities.record(
                organization_id=organization_id, lead_id=lead_id, actor_id=actor.id,
                activity_type=ActivityTypeEnum.BULK_ACTION,
                summary=f"Enrolled in campaign '{campaign.name}' by {actor.full_name}",
            )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.CREATE, resource_type="campaign_lead", resource_id=None,
            changes={
                "event": "lead_bulk_enrolled", "campaign_id": str(campaign_id),
                "requested": len(lead_ids), "enrolled": enrolled, "skipped": skipped,
            },
        )
        await self.db.commit()
        return BulkEnrollResponse(
            requested_count=len(lead_ids), enrolled_count=enrolled, skipped_count=skipped, errors=errors
        )

    async def enroll_by_filter(
        self, organization_id: uuid.UUID, campaign_id: uuid.UUID, filters: EnrollByFilterRequest, *, actor: User
    ) -> BulkEnrollResponse:
        # Reuses `LeadRepository.list_for_organization` exactly — the same
        # filter-building logic the Leads list route uses — never
        # reimplemented here. A large page_size stands in for "no limit"
        # since enrollment needs the full matching set, not one page of it.
        leads, _total = await self.leads.list_for_organization(
            organization_id,
            search=filters.search, status=filters.status, source=filters.source,
            owner_ids=filters.owner_id, tag_names=filters.tag, country=filters.country,
            industry=filters.industry, company=filters.company, is_favorite=filters.favorite,
            is_archived=filters.archived, lead_score_min=filters.lead_score_min,
            lead_score_max=filters.lead_score_max, priority_min=filters.priority_min,
            priority_max=filters.priority_max, created_from=filters.created_from,
            created_to=filters.created_to, updated_from=filters.updated_from,
            updated_to=filters.updated_to, page=1, page_size=10_000,
        )
        return await self.enroll_bulk(
            organization_id, campaign_id, [lead.id for lead in leads],
            sequence_id=filters.sequence_id, actor=actor,
        )

    async def unenroll(
        self, organization_id: uuid.UUID, campaign_lead_id: uuid.UUID, *, reason: str | None, actor: User
    ) -> CampaignLead:
        campaign_lead = await self.campaign_leads.get_by_id(campaign_lead_id, organization_id)
        if campaign_lead is None:
            raise NotFoundError("Enrollment not found.")
        if campaign_lead.status == CampaignLeadStatusEnum.OPTED_OUT.value:
            raise ValidationError("This lead is already unenrolled.")

        campaign_lead = await self.campaign_leads.update(
            campaign_lead,
            {
                "status": CampaignLeadStatusEnum.OPTED_OUT.value,
                "opted_out_at": datetime.now(timezone.utc), "next_action_at": None,
            },
        )
        await self.activities.record(
            organization_id=organization_id, lead_id=campaign_lead.lead_id, actor_id=actor.id,
            activity_type=ActivityTypeEnum.BULK_ACTION,
            summary=f"Unenrolled from campaign by {actor.full_name}" + (f" — {reason}" if reason else ""),
        )
        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.UPDATE, resource_type="campaign_lead", resource_id=campaign_lead.id,
            changes={"event": "lead_unenrolled", "reason": reason},
        )
        await self.db.commit()
        result = await self.campaign_leads.get_by_id(campaign_lead.id, organization_id)
        assert result is not None
        return result
