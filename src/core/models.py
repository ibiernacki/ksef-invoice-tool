from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Expense:
    description: str
    amount: Decimal
    date: date | None = None  # optional date the expense was incurred


@dataclass
class LeaveEntry:
    start: date
    end: date
    type: str  # "unpaid"
    working_days: int  # auto-calculated, excludes weekends and holidays


@dataclass
class MonthEntry:
    month: str  # "2026-04"
    days_total: int
    base_salary: Decimal
    invoice_number: str  # "0004"
    issued_date: date
    ref_person: str
    days_worked: int  # auto: days_total - sum(leave.working_days)
    expenses: list[Expense] = field(default_factory=list)
    leave: list[LeaveEntry] = field(default_factory=list)
    status: str = "draft"  # draft → generated → submitted → confirmed
    ksef_id: str | None = None


@dataclass
class InvoiceData:
    """Calculated invoice data, ready for PDF/XML generation."""

    # From MonthEntry
    month: str
    invoice_number: str
    issued_date: date
    selling_date: date
    payment_deadline: date
    ref_person: str

    # Calculated
    days_worked: int
    days_total: int
    base_salary: Decimal
    work_salary: Decimal
    expenses_total: Decimal
    additional_gross: Decimal  # expenses / 0.88
    final_amount: Decimal  # work_salary + additional_gross
    multiplier: Decimal  # final_amount / base_salary (used as quantity on invoice)
    net_value: Decimal  # round(base_salary * multiplier)

    # Metadata
    expenses: list[Expense] = field(default_factory=list)
    leave: list[LeaveEntry] = field(default_factory=list)
    status: str = "draft"
    ksef_id: str | None = None
