"""Available start times for a service on a given day.

A slot is offered when the whole service fits inside opening hours and does
not overlap any active (non-cancelled) appointment. Slots in the past are
never offered.
"""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def available_slots(
    day: date,
    duration_minutes: int,
    opens_at: time | None,
    closes_at: time | None,
    busy: Iterable[tuple[datetime, datetime]],
    now: datetime,
    step_minutes: int = 15,
) -> list[time]:
    if opens_at is None or closes_at is None:
        return []
    busy = list(busy)
    duration = timedelta(minutes=duration_minutes)
    cursor = datetime.combine(day, opens_at)
    closing = datetime.combine(day, closes_at)
    slots: list[time] = []
    while cursor + duration <= closing:
        end = cursor + duration
        if cursor > now and not any(overlaps(cursor, end, b_start, b_end) for b_start, b_end in busy):
            slots.append(cursor.time())
        cursor += timedelta(minutes=step_minutes)
    return slots
