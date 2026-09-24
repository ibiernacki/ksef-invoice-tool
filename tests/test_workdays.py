from datetime import date

from src.core.workdays import (
    count_working_days_in_month,
    count_working_days_in_range,
    easter_date,
    is_working_day,
    polish_holidays,
)


def test_easter_2026():
    assert easter_date(2026) == date(2026, 4, 5)


def test_easter_2025():
    assert easter_date(2025) == date(2025, 4, 20)


def test_boze_cialo_2026():
    """Boże Ciało = Easter + 60 days = 4 June 2026 (Thursday)."""
    holidays = polish_holidays(2026)
    assert date(2026, 6, 4) in holidays


def test_working_days_april_2026():
    """April 2026: 30 days, 22 weekdays, minus Easter Monday (6 April) = 21."""
    assert count_working_days_in_month(2026, 4) == 21


def test_working_days_june_2026():
    """June 2026: 22 weekdays, minus Boże Ciało (4 June, Thursday) = 21."""
    assert count_working_days_in_month(2026, 6) == 21


def test_working_days_january_2026():
    """January 2026: 22 weekdays, minus 1 Jan (Thu) and 6 Jan (Tue) = 20."""
    assert count_working_days_in_month(2026, 1) == 20


def test_working_days_may_2026():
    """May 2026: 21 weekdays, minus 1 May (Fri) and 3 May (Sun, not counted) = 20."""
    assert count_working_days_in_month(2026, 5) == 20


def test_leave_range_weekdays_only():
    """11-19 April 2026: Mon-Sun, should count 5 working days (Mon,Tue,Wed,Thu,Fri)."""
    # 11=Sat, 12=Sun, 13=Mon, 14=Tue, 15=Wed, 16=Thu, 17=Fri, 18=Sat, 19=Sun
    # Wait - let me check: April 2026
    # April 1 = Wednesday, so April 11 = Saturday
    # Actually: Apr 6 = Monday (Easter Monday = holiday)
    # Apr 11 = Saturday, Apr 13 = Monday, Apr 14=Tue, Apr 15=Wed, Apr 16=Thu, Apr 17=Fri
    # So 5 working days: 13,14,15,16,17
    count = count_working_days_in_range(date(2026, 4, 11), date(2026, 4, 19))
    assert count == 5


def test_is_working_day_weekend():
    assert not is_working_day(date(2026, 4, 11))  # Saturday
    assert not is_working_day(date(2026, 4, 12))  # Sunday


def test_is_working_day_holiday():
    assert not is_working_day(date(2026, 4, 6))  # Easter Monday


def test_is_working_day_normal():
    assert is_working_day(date(2026, 4, 7))  # Tuesday, not a holiday
