"""
The single place `Email.current_status` transitions are decided from an
incoming `EmailEvent`. Every event-recording path (open pixel, click
redirect, delivery webhook) calls `next_status(...)` instead of duplicating
the "never move status backwards" rule — see the model docstring on `Email`:
"We never update Email.status directly after send — we derive the current
status from the most recent EmailEvent."

The canonical lifecycle is linear (each stage strictly ahead of the last);
BOUNCED/FAILED/SPAM are terminal and reachable — and un-leavable — from any
point, since a bounce/complaint can arrive at any stage.
"""

from app.models.enums import EmailEventTypeEnum, EmailStatusEnum

_LIFECYCLE_ORDER: list[EmailStatusEnum] = [
    EmailStatusEnum.DRAFT,
    EmailStatusEnum.SCHEDULED,
    EmailStatusEnum.SENDING,
    EmailStatusEnum.SENT,
    EmailStatusEnum.DELIVERED,
    EmailStatusEnum.OPENED,
    EmailStatusEnum.CLICKED,
]
_TERMINAL_STATUSES = {EmailStatusEnum.BOUNCED, EmailStatusEnum.FAILED, EmailStatusEnum.SPAM}

# Which lifecycle/terminal status an incoming event pushes toward. QUEUED and
# UNSUBSCRIBED don't correspond to an Email.current_status value (unsubscribe
# is tracked on the Lead, not the Email) so they're absent — `next_status`
# returns `current` unchanged for them.
_EVENT_TARGET_STATUS: dict[EmailEventTypeEnum, EmailStatusEnum] = {
    EmailEventTypeEnum.SENT: EmailStatusEnum.SENT,
    EmailEventTypeEnum.DELIVERED: EmailStatusEnum.DELIVERED,
    EmailEventTypeEnum.OPENED: EmailStatusEnum.OPENED,
    EmailEventTypeEnum.CLICKED: EmailStatusEnum.CLICKED,
    EmailEventTypeEnum.BOUNCED: EmailStatusEnum.BOUNCED,
    EmailEventTypeEnum.COMPLAINED: EmailStatusEnum.SPAM,
    EmailEventTypeEnum.FAILED: EmailStatusEnum.FAILED,
}


def next_status(current: str, event_type: EmailEventTypeEnum) -> str:
    """Returns the `Email.current_status` value that should follow recording
    `event_type`, given the row's `current` status — `current` unchanged if
    the event doesn't move the lifecycle forward or the row is already in a
    terminal state."""
    target = _EVENT_TARGET_STATUS.get(event_type)
    if target is None:
        return current

    try:
        current_status = EmailStatusEnum(current)
    except ValueError:
        return current

    if current_status in _TERMINAL_STATUSES:
        return current  # terminal states are sticky — no lifecycle event un-terminates them

    if target in _TERMINAL_STATUSES:
        return target.value  # a bounce/complaint/failure always wins, from any point

    current_index = _LIFECYCLE_ORDER.index(current_status) if current_status in _LIFECYCLE_ORDER else -1
    target_index = _LIFECYCLE_ORDER.index(target)
    return target.value if target_index > current_index else current
