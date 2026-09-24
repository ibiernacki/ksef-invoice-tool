"""Test calculator against known invoice data."""

from datetime import date
from decimal import Decimal

from src.core.calculator import calculate_invoice
from src.core.models import Expense, MonthEntry


def test_calculation_with_expenses():
    """Verify calculation logic: base salary + expenses / 0.88."""
    expenses = [
        Expense(description="uber", amount=Decimal("21.66")),
        Expense(description="uber", amount=Decimal("22.13")),
        Expense(description="flight", amount=Decimal("120")),
        Expense(description="flight", amount=Decimal("59")),
        Expense(description="flight", amount=Decimal("1073.68")),
        Expense(description="hotel", amount=Decimal("839.91")),
    ]

    entry = MonthEntry(
        month="2026-03",
        days_total=22,
        base_salary=Decimal("20000"),
        invoice_number="0003",
        issued_date=date(2026, 3, 31),
        ref_person="Anna Svensson",
        days_worked=22,
        expenses=expenses,
    )

    invoice = calculate_invoice(entry)

    # Verify expenses total
    assert invoice.expenses_total == Decimal("2136.38")

    # Verify additional_gross = 2136.38 / 0.88
    expected_additional = Decimal("2136.38") / Decimal("0.88")
    assert invoice.additional_gross == expected_additional

    # Verify final amount
    expected_final = Decimal("20000") + expected_additional
    assert invoice.final_amount == expected_final

    # Verify multiplier = final / base
    expected_multiplier = expected_final / Decimal("20000")
    assert invoice.multiplier == expected_multiplier

    # Multiplier should be > 1 (expenses added)
    assert invoice.multiplier > Decimal("1")


def test_full_month_no_expenses():
    """Full month with no expenses should have multiplier = 1.0."""
    entry = MonthEntry(
        month="2026-04",
        days_total=21,
        base_salary=Decimal("20000"),
        invoice_number="0004",
        issued_date=date(2026, 4, 30),
        ref_person="Anna Svensson",
        days_worked=21,
    )

    invoice = calculate_invoice(entry)
    assert invoice.multiplier == Decimal("1")
    assert invoice.net_value == Decimal("20000")


def test_partial_month():
    """Working 16 out of 21 days should reduce work salary proportionally."""
    entry = MonthEntry(
        month="2026-04",
        days_total=21,
        base_salary=Decimal("20000"),
        invoice_number="0004",
        issued_date=date(2026, 4, 30),
        ref_person="Anna Svensson",
        days_worked=16,
    )

    invoice = calculate_invoice(entry)

    expected_work = (Decimal("16") / Decimal("21")) * Decimal("20000")
    assert invoice.work_salary == expected_work
    assert invoice.multiplier == expected_work / Decimal("20000")


def test_leave_reduces_days():
    """Leave entries should reduce days_worked in calculation."""
    from src.core.models import LeaveEntry

    entry = MonthEntry(
        month="2026-04",
        days_total=21,
        base_salary=Decimal("20000"),
        invoice_number="0004",
        issued_date=date(2026, 4, 30),
        ref_person="Anna Svensson",
        days_worked=16,  # 21 - 5 days leave
        leave=[
            LeaveEntry(
                start=date(2026, 4, 11),
                end=date(2026, 4, 19),
                type="unpaid",
                working_days=5,
            )
        ],
    )

    invoice = calculate_invoice(entry)
    assert invoice.days_worked == 16


def test_payment_deadline():
    """Payment deadline should be 7 days after issued date."""
    entry = MonthEntry(
        month="2026-04",
        days_total=21,
        base_salary=Decimal("20000"),
        invoice_number="0004",
        issued_date=date(2026, 4, 30),
        ref_person="Anna Svensson",
        days_worked=21,
    )

    invoice = calculate_invoice(entry)
    assert invoice.payment_deadline == date(2026, 5, 7)
