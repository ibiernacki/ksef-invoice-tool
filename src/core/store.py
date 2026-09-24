"""YAML data store for month entries."""

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

from .models import Expense, LeaveEntry, MonthEntry
from .workdays import count_working_days_in_month, count_working_days_in_range

# Project root — resolved relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"Missing {CONFIG_PATH.name}. Create it with:\n"
            f"  cp config.example.yaml config.yaml\n"
            f"and fill in your seller/buyer data (or ask Claude Code to run the invoice-setup skill)."
        )
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _month_path(month: str) -> Path:
    """Return path for a month YAML file. month format: '2026-04'."""
    year, m = month.split("-")
    return DATA_DIR / year / f"{m}.yaml"


def _parse_month_entry(data: dict) -> MonthEntry:
    """Parse a YAML dict into a MonthEntry."""
    expenses = [
        Expense(
            description=e["description"],
            amount=Decimal(str(e["amount"])),
            date=date.fromisoformat(str(e["date"])) if e.get("date") else None,
        )
        for e in data.get("expenses", [])
    ]
    leave = [
        LeaveEntry(
            start=date.fromisoformat(str(le["start"])),
            end=date.fromisoformat(str(le["end"])),
            type=le["type"],
            working_days=le["working_days"],
        )
        for le in data.get("leave", [])
    ]
    return MonthEntry(
        month=data["month"],
        days_total=data["days_total"],
        base_salary=Decimal(str(data["base_salary"])),
        invoice_number=data["invoice_number"],
        issued_date=date.fromisoformat(str(data["issued_date"])),
        ref_person=data["ref_person"],
        days_worked=data["days_worked"],
        expenses=expenses,
        leave=leave,
        status=data.get("status", "draft"),
        ksef_id=data.get("ksef_id"),
    )


def _serialize_month_entry(entry: MonthEntry) -> dict:
    """Serialize MonthEntry to a dict for YAML output."""
    data: dict = {
        "month": entry.month,
        "days_total": entry.days_total,
        "base_salary": float(entry.base_salary),
        "invoice_number": entry.invoice_number,
        "issued_date": entry.issued_date.isoformat(),
        "ref_person": entry.ref_person,
        "days_worked": entry.days_worked,
        "status": entry.status,
        "ksef_id": entry.ksef_id,
    }
    if entry.leave:
        data["leave"] = [
            {
                "start": le.start.isoformat(),
                "end": le.end.isoformat(),
                "type": le.type,
                "working_days": le.working_days,
            }
            for le in entry.leave
        ]
    if entry.expenses:
        data["expenses"] = [
            {
                "description": e.description,
                "amount": float(e.amount),
                **({"date": e.date.isoformat()} if e.date else {}),
            }
            for e in entry.expenses
        ]
    return data


def _existing_invoice_numbers(year: str, exclude_month: str | None = None) -> dict[int, str]:
    """Map each used invoice number (as int) to the month that owns it, for a year.

    `exclude_month` ('2026-05') is skipped so a month never clashes with itself.
    """
    year_dir = DATA_DIR / year
    if not year_dir.exists():
        return {}
    numbers: dict[int, str] = {}
    for path in sorted(year_dir.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        if data["month"] == exclude_month:
            continue
        numbers[int(data["invoice_number"])] = data["month"]
    return numbers


def _invoice_number_for_month(month: str) -> str:
    """Invoice number derived from the month ordinal: 2026-01 -> 0001, ...12 -> 0012.

    Assumes one invoice per month. The uniqueness guard in `save_month` catches
    the (so far never-occurred) case of two invoices in the same month.
    """
    return f"{int(month.split('-')[1]):04d}"


def _recalculate_days_worked(entry: MonthEntry) -> None:
    """Recalculate days_worked based on days_total and leave."""
    leave_days = sum(le.working_days for le in entry.leave)
    entry.days_worked = entry.days_total - leave_days


def get_or_create_month(month: str) -> MonthEntry:
    """Load a month entry from YAML, or create a new one with defaults."""
    path = _month_path(month)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
        return _parse_month_entry(data)

    # Create new entry with defaults
    config = load_config()
    year, m = int(month.split("-")[0]), int(month.split("-")[1])
    days_total = count_working_days_in_month(year, m)

    # Last day of month as issued date
    last_day = calendar.monthrange(year, m)[1]
    issued_date = date(year, m, last_day)

    # Invoice number derived from the month (one invoice per month)
    invoice_number = _invoice_number_for_month(month)

    entry = MonthEntry(
        month=month,
        days_total=days_total,
        base_salary=Decimal(str(config["invoice"]["base_salary"])),
        invoice_number=invoice_number,
        issued_date=issued_date,
        ref_person=config["buyer"]["ref_person"],
        days_worked=days_total,
    )

    save_month(entry)
    return entry


def save_month(entry: MonthEntry) -> None:
    """Save a month entry to YAML.

    Rejects a save that would reuse an invoice number already owned by another
    month in the same year — duplicate numbers are rejected by KSeF and clobber
    each other's output files.
    """
    year = entry.month.split("-")[0]
    clash = _existing_invoice_numbers(year, exclude_month=entry.month).get(
        int(entry.invoice_number)
    )
    if clash is not None:
        raise ValueError(
            f"Invoice number {entry.invoice_number}/{year} is already used by "
            f"month {clash}; invoice numbers must be unique per year."
        )

    path = _month_path(entry.month)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _serialize_month_entry(entry)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def add_expense(
    month: str, description: str, amount: Decimal, expense_date: date | None = None
) -> MonthEntry:
    """Add an expense to a month entry (auto-creates month if needed)."""
    entry = get_or_create_month(month)
    entry.expenses.append(Expense(description=description, amount=amount, date=expense_date))
    save_month(entry)
    return entry


def add_leave(month: str, start: date, end: date, leave_type: str = "unpaid") -> MonthEntry:
    """Add a leave entry (auto-creates month if needed)."""
    entry = get_or_create_month(month)
    working_days = count_working_days_in_range(start, end)
    entry.leave.append(
        LeaveEntry(start=start, end=end, type=leave_type, working_days=working_days)
    )
    _recalculate_days_worked(entry)
    save_month(entry)
    return entry
