"""Invoice calculation logic."""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from .models import InvoiceData, MonthEntry


def calculate_invoice(entry: MonthEntry) -> InvoiceData:
    """Calculate invoice data from a month entry."""
    # Use days_worked from entry (already calculated by store with leave deductions)
    days_worked = entry.days_worked

    # Work salary proportional to days worked
    work_salary = (Decimal(days_worked) / Decimal(entry.days_total)) * entry.base_salary

    # Expenses grossed up for 12% ryczałt
    expenses_total = sum((e.amount for e in entry.expenses), Decimal(0))
    tax_divisor = Decimal("0.88")  # 1 - 0.12
    additional_gross = expenses_total / tax_divisor if expenses_total else Decimal(0)

    # Final amount
    final_amount = work_salary + additional_gross

    # Multiplier (quantity on invoice)
    multiplier = final_amount / entry.base_salary

    # Net value = base_salary * multiplier, rounded to whole PLN
    net_value = (entry.base_salary * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    return InvoiceData(
        month=entry.month,
        invoice_number=entry.invoice_number,
        issued_date=entry.issued_date,
        selling_date=entry.issued_date,
        payment_deadline=entry.issued_date + timedelta(days=7),
        ref_person=entry.ref_person,
        days_worked=days_worked,
        days_total=entry.days_total,
        base_salary=entry.base_salary,
        work_salary=work_salary,
        expenses_total=expenses_total,
        additional_gross=additional_gross,
        final_amount=final_amount,
        multiplier=multiplier,
        net_value=net_value,
        expenses=entry.expenses,
        leave=entry.leave,
        status=entry.status,
        ksef_id=entry.ksef_id,
    )
