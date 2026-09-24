"""Tests for invoice number assignment and uniqueness validation.

Numbering rule: one invoice per month, so the number is the month ordinal —
January -> 0001, ..., December -> 0012.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.core import store
from src.core.models import MonthEntry


def _entry(month: str, number: str) -> MonthEntry:
    year, m = month.split("-")
    return MonthEntry(
        month=month,
        days_total=20,
        base_salary=Decimal("20000"),
        invoice_number=number,
        issued_date=date(int(year), int(m), 28),
        ref_person="Anna Svensson",
        days_worked=20,
    )


@pytest.fixture
def temp_store(tmp_path, monkeypatch):
    """Point the store at an isolated data dir."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(store, "DATA_DIR", data_dir)
    return data_dir


@pytest.mark.parametrize(
    "month,expected",
    [
        ("2026-01", "0001"),
        ("2026-02", "0002"),
        ("2026-04", "0004"),
        ("2026-05", "0005"),
        ("2026-12", "0012"),
    ],
)
def test_invoice_number_matches_month_ordinal(month, expected):
    assert store._invoice_number_for_month(month) == expected


def test_save_rejects_duplicate_number_across_months(temp_store):
    """Saving a month with a number already used by another month raises."""
    store.save_month(_entry("2026-04", "0004"))
    with pytest.raises(ValueError, match="already used"):
        store.save_month(_entry("2026-05", "0004"))


def test_resaving_same_month_is_allowed(temp_store):
    """A month may be re-saved with its own existing number."""
    store.save_month(_entry("2026-04", "0004"))
    store.save_month(_entry("2026-04", "0004"))  # should not raise
    assert store._existing_invoice_numbers("2026") == {4: "2026-04"}
