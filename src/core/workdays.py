"""Polish working days calculator with public holidays support."""

from datetime import date, timedelta


def easter_date(year: int) -> date:
    """Calculate Easter Sunday using the anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def polish_holidays(year: int) -> set[date]:
    """Return all Polish public holidays for a given year."""
    easter = easter_date(year)
    return {
        date(year, 1, 1),  # Nowy Rok
        date(year, 1, 6),  # Trzech Króli
        easter,  # Wielkanoc (niedziela)
        easter + timedelta(days=1),  # Poniedziałek Wielkanocny
        date(year, 5, 1),  # Święto Pracy
        date(year, 5, 3),  # Święto Konstytucji
        easter + timedelta(days=60),  # Boże Ciało
        date(year, 8, 15),  # Wniebowzięcie NMP
        date(year, 11, 1),  # Wszystkich Świętych
        date(year, 11, 11),  # Święto Niepodległości
        date(year, 12, 25),  # Boże Narodzenie
        date(year, 12, 26),  # Drugi dzień Bożego Narodzenia
    }


def is_working_day(d: date) -> bool:
    """Check if a date is a working day (Mon-Fri, not a Polish holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in polish_holidays(d.year)


def count_working_days_in_month(year: int, month: int) -> int:
    """Count working days in a given month."""
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1)
    else:
        last = date(year, month + 1, 1)

    count = 0
    current = first
    while current < last:
        if is_working_day(current):
            count += 1
        current += timedelta(days=1)
    return count


def count_working_days_in_range(start: date, end: date) -> int:
    """Count working days in a date range (inclusive on both ends)."""
    count = 0
    current = start
    while current <= end:
        if is_working_day(current):
            count += 1
        current += timedelta(days=1)
    return count
