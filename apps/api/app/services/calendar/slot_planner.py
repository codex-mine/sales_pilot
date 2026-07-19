"""
Pure, provider-agnostic open-slot computation — given a list of busy blocks
(already fetched from whichever `CalendarClient`), works out which
business-hours slots are actually free. Kept separate from
`calendar_client.py` (provider I/O) and `meeting_service.py` (orchestration)
so the scheduling arithmetic itself is trivially unit-testable without
mocking a calendar API.

V1 uses one fixed business-hours window (`settings.meeting_business_hours_*`)
applied in UTC — a full per-owner availability-rules table is out of scope
per the module spec ("a simple business-hours default is sufficient scope").
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

_SLOT_STEP_MINUTES = 30
_WEEKEND = {5, 6}  # Saturday, Sunday


@dataclass
class BusyBlock:
    start: datetime
    end: datetime


def is_slot_busy(start: datetime, end: datetime, busy_blocks: list[BusyBlock]) -> bool:
    return any(start < block.end and end > block.start for block in busy_blocks)


def _round_up_to_step(dt: datetime, step_minutes: int = _SLOT_STEP_MINUTES) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    remainder = dt.minute % step_minutes
    if remainder == 0:
        return dt
    return dt + timedelta(minutes=step_minutes - remainder)


def generate_candidate_slots(
    busy_blocks: list[BusyBlock],
    *,
    now: datetime,
    duration_minutes: int,
    slot_count: int,
    window_days: int,
    business_start_hour: int,
    business_end_hour: int,
) -> list[dict[str, datetime]]:
    """Scans forward from `now` across up to `window_days` business days,
    returning the first `slot_count` open slots of `duration_minutes` each,
    aligned to :00/:30 boundaries within the business-hours window."""
    duration = timedelta(minutes=duration_minutes)
    candidates: list[dict[str, datetime]] = []
    day_cursor: date = now.date()
    days_scanned = 0

    while len(candidates) < slot_count and days_scanned <= window_days:
        if day_cursor.weekday() not in _WEEKEND:
            day_start = datetime.combine(day_cursor, time(hour=business_start_hour), tzinfo=timezone.utc)
            day_end = datetime.combine(day_cursor, time(hour=business_end_hour), tzinfo=timezone.utc)
            slot_start = _round_up_to_step(max(day_start, now))

            while slot_start + duration <= day_end and len(candidates) < slot_count:
                slot_end = slot_start + duration
                if not is_slot_busy(slot_start, slot_end, busy_blocks):
                    candidates.append({"start": slot_start, "end": slot_end})
                slot_start += timedelta(minutes=_SLOT_STEP_MINUTES)

        day_cursor += timedelta(days=1)
        days_scanned += 1

    return candidates
