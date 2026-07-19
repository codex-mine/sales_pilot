"""
The single place a Lead's AI/engagement-driven status transitions are
decided — mirrors `app.services.email.email_status_resolver.next_status`
for the identical reason: several modules (Research, Email Generation,
Email Tracking, Inbox) each want to advance `Lead.status` as a side effect
of something happening, and none of them should be allowed to move it
backwards.

The canonical ordering is the one `LeadStatusEnum`'s own docstring already
documents: "new -> contacted -> interested -> demo_scheduled -> proposal ->
negotiation -> won / lost / unqualified" — this module just makes it
computable instead of re-describing it in prose at each call site.
"""

from app.models.enums import LeadStatusEnum

_LEAD_LIFECYCLE_ORDER: list[LeadStatusEnum] = [
    LeadStatusEnum.NEW,
    LeadStatusEnum.RESEARCHING,
    LeadStatusEnum.RESEARCH_DONE,
    LeadStatusEnum.EMAIL_GENERATED,
    LeadStatusEnum.CONTACTED,
    LeadStatusEnum.OPENED,
    LeadStatusEnum.REPLIED,
    LeadStatusEnum.INTERESTED,
    LeadStatusEnum.QUALIFIED,
    LeadStatusEnum.DEMO_SCHEDULED,
    LeadStatusEnum.PROPOSAL,
    LeadStatusEnum.NEGOTIATION,
]
# WON/LOST/UNQUALIFIED are sales-outcome terminals; BOUNCED/UNSUBSCRIBED are
# suppression terminals. Both kinds are "sticky" — once there, no
# engagement-driven event (an open, a reply, an AI classification) may move
# the lead back into the lifecycle.
_LEAD_TERMINAL_STATUSES = {
    LeadStatusEnum.WON, LeadStatusEnum.LOST, LeadStatusEnum.UNQUALIFIED,
    LeadStatusEnum.BOUNCED, LeadStatusEnum.UNSUBSCRIBED,
}


def next_lead_status(current: str, target: LeadStatusEnum) -> str:
    """Returns the `Lead.status` value that should follow an engagement/AI
    event proposing `target`, given the lead's `current` status — `current`
    unchanged if `target` doesn't move the lead forward or it's already
    terminal."""
    try:
        current_status = LeadStatusEnum(current)
    except ValueError:
        return current

    if current_status in _LEAD_TERMINAL_STATUSES:
        return current  # terminal is sticky

    if target in _LEAD_TERMINAL_STATUSES:
        return target.value  # suppression/outcome terminals always win

    if current_status not in _LEAD_LIFECYCLE_ORDER or target not in _LEAD_LIFECYCLE_ORDER:
        return current  # an out-of-lifecycle target (e.g. a status this resolver doesn't model) never applies here

    current_index = _LEAD_LIFECYCLE_ORDER.index(current_status)
    target_index = _LEAD_LIFECYCLE_ORDER.index(target)
    return target.value if target_index > current_index else current
