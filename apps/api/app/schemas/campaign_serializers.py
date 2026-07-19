"""ORM -> response-schema mapping for the Campaigns module."""

from app.models.campaigns.models import Campaign, CampaignLead, Sequence, SequenceStep
from app.models.enums import CampaignLeadStatusEnum
from app.schemas.campaigns import (
    CampaignFunnelCounts,
    CampaignLeadLeadSummary,
    CampaignLeadResponse,
    CampaignOwnerResponse,
    CampaignResponse,
    SequenceResponse,
    SequenceStepResponse,
    SequenceStepTemplateSummary,
)
from app.services.campaigns.campaign_settings import get_requires_approval
from app.services.campaigns.sequence_service import split_condition

_FUNNEL_KEYS = (
    CampaignLeadStatusEnum.ENROLLED.value, CampaignLeadStatusEnum.IN_PROGRESS.value,
    CampaignLeadStatusEnum.REPLIED.value, CampaignLeadStatusEnum.MEETING_BOOKED.value,
    CampaignLeadStatusEnum.COMPLETED.value, CampaignLeadStatusEnum.OPTED_OUT.value,
    CampaignLeadStatusEnum.BOUNCED.value,
)


def _funnel(counts: dict[str, int]) -> CampaignFunnelCounts:
    return CampaignFunnelCounts(
        enrolled=counts.get(CampaignLeadStatusEnum.ENROLLED.value, 0),
        in_progress=counts.get(CampaignLeadStatusEnum.IN_PROGRESS.value, 0),
        replied=counts.get(CampaignLeadStatusEnum.REPLIED.value, 0),
        meeting_booked=counts.get(CampaignLeadStatusEnum.MEETING_BOOKED.value, 0),
        completed=counts.get(CampaignLeadStatusEnum.COMPLETED.value, 0),
        opted_out=counts.get(CampaignLeadStatusEnum.OPTED_OUT.value, 0),
        bounced=counts.get(CampaignLeadStatusEnum.BOUNCED.value, 0),
    )


def serialize_campaign(
    campaign: Campaign, *, enrolled_count: int = 0, funnel_counts: dict[str, int] | None = None
) -> CampaignResponse:
    return CampaignResponse(
        id=str(campaign.id),
        organization_id=str(campaign.organization_id),
        owner=(
            CampaignOwnerResponse(id=str(campaign.owner.id), full_name=campaign.owner.full_name, email=campaign.owner.email)
            if campaign.owner
            else None
        ),
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        goal=campaign.goal,
        target_industry=campaign.target_industry,
        target_company_size=campaign.target_company_size,
        target_job_titles=campaign.target_job_titles,
        value_proposition=campaign.value_proposition,
        daily_send_limit=campaign.daily_send_limit,
        timezone=campaign.timezone,
        send_days=campaign.send_days or [],
        send_start_hour=campaign.send_start_hour,
        send_end_hour=campaign.send_end_hour,
        requires_approval=get_requires_approval(campaign),
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        enrolled_count=enrolled_count,
        funnel=_funnel(funnel_counts) if funnel_counts is not None else None,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _template_summary(template) -> SequenceStepTemplateSummary | None:
    if template is None:
        return None
    open_rate = (template.total_opened / template.total_sent * 100) if template.total_sent else 0.0
    reply_rate = (template.total_replied / template.total_sent * 100) if template.total_sent else 0.0
    return SequenceStepTemplateSummary(
        id=str(template.id), name=template.name, subject=template.subject,
        total_sent=template.total_sent, total_opened=template.total_opened, total_replied=template.total_replied,
        open_rate=round(open_rate, 1), reply_rate=round(reply_rate, 1),
    )


def serialize_sequence_step(step: SequenceStep) -> SequenceStepResponse:
    rules, content_source = split_condition(step.condition)
    return SequenceStepResponse(
        id=str(step.id),
        sequence_id=str(step.sequence_id),
        step_type=step.step_type,
        step_order=step.step_order,
        delay_days=step.delay_days,
        delay_hours=step.delay_hours,
        email_template_id=str(step.email_template_id) if step.email_template_id else None,
        email_template=_template_summary(step.email_template),
        content_source=content_source,
        subject_override=step.subject_override,
        body_override=step.body_override,
        condition=rules or None,
        is_active=step.is_active,
    )


def serialize_sequence(sequence: Sequence) -> SequenceResponse:
    steps = sorted(sequence.steps, key=lambda s: s.step_order)
    return SequenceResponse(
        id=str(sequence.id),
        campaign_id=str(sequence.campaign_id),
        name=sequence.name,
        description=sequence.description,
        is_active=sequence.is_active,
        steps=[serialize_sequence_step(step) for step in steps],
        created_at=sequence.created_at,
    )


def serialize_campaign_lead(campaign_lead: CampaignLead) -> CampaignLeadResponse:
    lead = campaign_lead.lead
    next_step = campaign_lead.next_step
    return CampaignLeadResponse(
        id=str(campaign_lead.id),
        campaign_id=str(campaign_lead.campaign_id),
        campaign_name=campaign_lead.campaign.name if campaign_lead.campaign else None,
        lead=(
            CampaignLeadLeadSummary(
                id=str(lead.id), full_name=lead.full_name, email=lead.email,
                company_name=lead.company_name, status=lead.status,
            )
            if lead
            else None
        ),
        sequence_id=str(campaign_lead.sequence_id) if campaign_lead.sequence_id else None,
        status=campaign_lead.status,
        current_step_order=campaign_lead.current_step_order,
        next_step_id=str(campaign_lead.next_step_id) if campaign_lead.next_step_id else None,
        next_step_type=next_step.step_type if next_step else None,
        next_action_at=campaign_lead.next_action_at,
        enrolled_at=campaign_lead.enrolled_at,
        completed_at=campaign_lead.completed_at,
        opted_out_at=campaign_lead.opted_out_at,
    )
