"""
Pure send-window roll-forward arithmetic for Campaign sequences — given a
candidate datetime, returns the next datetime that falls within the
Campaign's configured `send_days`/`send_start_hour`/`send_end_hour` (in the
campaign's own timezone). This is the scheduling-time counterpart to
`EmailSendingService._within_send_window`'s send-time check — same
days/hours reasoning, computing "when should this run" instead of checking
"is now valid".
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_DEFAULT_SEND_DAYS = _DAY_NAMES[:5]


def roll_forward_into_window(
    candidate: datetime, *, send_days: list[str] | None, send_start_hour: int, send_end_hour: int, tz_name: str
) -> datetime:
    """`candidate` must be timezone-aware. Returns a UTC datetime landing on
    one of `send_days`, between `send_start_hour` and `send_end_hour` in
    `tz_name` — `candidate` unchanged if already valid, otherwise the next
    valid slot's start."""
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except Exception:  # noqa: BLE001 — bad/unknown tz string, fall back safely
        tz = ZoneInfo("UTC")
    send_days_set = {d.lower() for d in (send_days or _DEFAULT_SEND_DAYS)}

    local = candidate.astimezone(tz)
    for _ in range(8):  # at most one full week forward — always terminates
        day_name = _DAY_NAMES[local.weekday()]
        if day_name in send_days_set:
            if local.hour < send_start_hour:
                local = local.replace(hour=send_start_hour, minute=0, second=0, microsecond=0)
                return local.astimezone(timezone.utc)
            if local.hour < send_end_hour:
                return local.astimezone(timezone.utc)
        local = (local + timedelta(days=1)).replace(hour=send_start_hour, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)
