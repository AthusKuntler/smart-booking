from datetime import date, datetime, time

from app.availability import available_slots

DAY = date(2030, 1, 7)  # a Monday far in the future
NOW = datetime(2030, 1, 1, 12, 0)


def t(hhmm: str) -> time:
    return time.fromisoformat(hhmm)


def test_slots_fit_inside_opening_hours():
    slots = available_slots(DAY, 60, t("09:00"), t("11:00"), [], NOW, step_minutes=30)
    assert slots == [t("09:00"), t("09:30"), t("10:00")]  # 10:30 would end after closing


def test_busy_time_is_excluded_including_partial_overlaps():
    busy = [(datetime(2030, 1, 7, 10, 0), datetime(2030, 1, 7, 10, 30))]
    slots = available_slots(DAY, 60, t("09:00"), t("12:00"), busy, NOW, step_minutes=30)
    # 09:30 and 10:00 would overlap 10:00-10:30
    assert slots == [t("09:00"), t("10:30"), t("11:00")]


def test_back_to_back_booking_is_allowed():
    busy = [(datetime(2030, 1, 7, 9, 0), datetime(2030, 1, 7, 10, 0))]
    slots = available_slots(DAY, 60, t("09:00"), t("11:00"), busy, NOW, step_minutes=60)
    assert slots == [t("10:00")]


def test_closed_day_has_no_slots():
    assert available_slots(DAY, 30, None, None, [], NOW) == []


def test_past_times_are_not_offered():
    now = datetime(2030, 1, 7, 10, 10)
    slots = available_slots(DAY, 30, t("09:00"), t("11:00"), [], now, step_minutes=30)
    assert slots == [t("10:30")]
