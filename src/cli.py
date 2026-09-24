"""Invoice CLI — thin wrapper over core logic."""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import typer

from .core.calculator import calculate_invoice
from .core.store import (
    PROJECT_ROOT,
    add_expense,
    add_leave,
    get_or_create_month,
    load_config,
    save_month,
)

app = typer.Typer(help="Invoice automation tool with KSeF integration")

OUTPUT_DIR = PROJECT_ROOT / "output"


@app.command()
def show(month: str = typer.Argument(help="Month in YYYY-MM format, e.g. 2026-04")):
    """Show invoice calculation for a given month."""
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)

    typer.echo(f"\n{'=' * 50}")
    typer.echo(f"  Invoice {invoice.invoice_number}/{invoice.month[:4]}")
    typer.echo(f"  Month: {invoice.month}")
    typer.echo(f"{'=' * 50}")
    typer.echo(f"  Days worked:      {invoice.days_worked}/{invoice.days_total}")
    typer.echo(f"  Base salary:      {invoice.base_salary:>10} PLN")
    typer.echo(f"  Work salary:      {invoice.work_salary:>10.2f} PLN")

    if invoice.expenses:
        typer.echo(f"\n  Expenses:")
        for e in invoice.expenses:
            date_str = f" [{e.date.isoformat()}]" if e.date else ""
            typer.echo(f"    - {e.description:<25} {e.amount:>10.2f} PLN{date_str}")
        typer.echo(f"  Expenses total:   {invoice.expenses_total:>10.2f} PLN")
        typer.echo(f"  After tax adj:    {invoice.additional_gross:>10.2f} PLN (/0.88)")

    if invoice.leave:
        typer.echo(f"\n  Leave:")
        for le in invoice.leave:
            typer.echo(f"    - {le.start} to {le.end} ({le.type}, {le.working_days} working days)")

    typer.echo(f"\n  Final amount:     {invoice.final_amount:>10.2f} PLN")
    typer.echo(f"  Multiplier:       {invoice.multiplier:>10.4f}")
    typer.echo(f"  Net value:        {invoice.net_value:>10} PLN")
    typer.echo(f"  Status:           {invoice.status}")
    typer.echo(f"{'=' * 50}\n")


@app.command("add-expense")
def cmd_add_expense(
    month: str = typer.Option(help="Month in YYYY-MM format"),
    desc: str = typer.Option(help="Expense description"),
    amount: float = typer.Option(help="Expense amount in PLN"),
    expense_date: str = typer.Option(
        None, "--date", help="Optional date the expense was incurred (YYYY-MM-DD)"
    ),
):
    """Add an expense to a month."""
    parsed_date = date.fromisoformat(expense_date) if expense_date else None
    entry = add_expense(month, desc, Decimal(str(amount)), parsed_date)
    typer.echo(f"Added expense '{desc}' ({amount} PLN) to {month}")
    typer.echo(f"Total expenses: {sum(e.amount for e in entry.expenses):.2f} PLN")


@app.command("add-leave")
def cmd_add_leave(
    month: str = typer.Option(help="Month in YYYY-MM format"),
    start: str = typer.Option(help="Leave start date (YYYY-MM-DD)"),
    end: str = typer.Option(help="Leave end date (YYYY-MM-DD)"),
    type: str = typer.Option("unpaid", help="Leave type"),
):
    """Add a leave period to a month."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    entry = add_leave(month, start_date, end_date, type)
    leave_entry = entry.leave[-1]
    typer.echo(
        f"Added {type} leave {start} to {end} ({leave_entry.working_days} working days) to {month}"
    )
    typer.echo(f"Days worked: {entry.days_worked}/{entry.days_total}")


@app.command()
def generate(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Generate PDF invoice for a given month."""
    config = load_config()
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    year = month[:4]
    filename = f"invoice_{invoice.invoice_number}_{year}.pdf"
    output_path = OUTPUT_DIR / filename

    from .core.pdf_generator import generate_pdf

    generate_pdf(
        invoice=invoice,
        seller=config["seller"],
        buyer=config["buyer"],
        output_path=str(output_path),
    )

    entry.status = "generated"
    save_month(entry)

    typer.echo(f"Generated: {output_path}")
    typer.echo(f"  Net value: {invoice.net_value} PLN | Multiplier: {float(invoice.multiplier):.4f}")


@app.command()
def preview(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Generate and open PDF invoice."""
    from .core.pdf_generator import generate_pdf

    config = load_config()
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    year = month[:4]
    filename = f"invoice_{invoice.invoice_number}_{year}.pdf"
    output_path = OUTPUT_DIR / filename

    generate_pdf(
        invoice=invoice,
        seller=config["seller"],
        buyer=config["buyer"],
        output_path=str(output_path),
    )

    typer.echo(f"Generated: {output_path}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(output_path)])
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", str(output_path)])


@app.command("generate-xml")
def cmd_generate_xml(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Generate KSeF FA(3) XML for a given month."""
    from .core.ksef_xml import generate_invoice_xml

    config = load_config()
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    year = month[:4]
    filename = f"invoice_{invoice.invoice_number}_{year}.xml"
    output_path = OUTPUT_DIR / filename

    xml_bytes = generate_invoice_xml(
        invoice=invoice,
        seller=config["seller"],
        buyer=config["buyer"],
    )

    output_path.write_bytes(xml_bytes)
    typer.echo(f"Generated XML: {output_path}")


@app.command()
def validate(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Validate invoice XML with @ksefuj/validator (requires npx)."""
    year = month[:4]
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)
    filename = f"invoice_{invoice.invoice_number}_{year}.xml"
    xml_path = OUTPUT_DIR / filename

    if not xml_path.exists():
        typer.echo(f"XML not found: {xml_path}. Run 'invoice generate-xml {month}' first.")
        raise typer.Exit(1)

    typer.echo(f"Validating: {xml_path}")
    result = subprocess.run(
        ["npx", "@ksefuj/validator", str(xml_path)],
        capture_output=True,
        text=True,
    )
    typer.echo(result.stdout)
    if result.stderr:
        typer.echo(result.stderr)
    if result.returncode != 0:
        typer.echo("Validation FAILED")
        raise typer.Exit(1)
    typer.echo("Validation PASSED")


@app.command()
def submit(
    month: str = typer.Argument(help="Month in YYYY-MM format"),
    env: str = typer.Option("test", help="KSeF environment: test, demo, prod"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only, do not submit"),
):
    """Submit invoice to KSeF."""
    from .core.ksef_xml import generate_invoice_xml

    config = load_config()
    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)

    # Generate XML
    xml_bytes = generate_invoice_xml(
        invoice=invoice,
        seller=config["seller"],
        buyer=config["buyer"],
    )

    # Save XML
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    year = month[:4]
    xml_filename = f"invoice_{invoice.invoice_number}_{year}.xml"
    xml_path = OUTPUT_DIR / xml_filename
    xml_path.write_bytes(xml_bytes)
    typer.echo(f"Generated XML: {xml_path}")

    if dry_run:
        typer.echo("Dry run — XML generated, not submitted.")
        return

    if env == "prod":
        typer.confirm("You are about to submit to PRODUCTION KSeF. Continue?", abort=True)

    from .core.ksef_client_wrapper import submit_invoice

    typer.echo(f"Submitting to KSeF ({env})...")
    result = submit_invoice(invoice_xml=xml_bytes, env=env)

    typer.echo(f"Submitted! Reference: {result.reference_number}")
    if result.ksef_number:
        typer.echo(f"KSeF number: {result.ksef_number}")
        entry.ksef_id = result.ksef_number

    entry.status = "submitted"
    save_month(entry)

    # Save UPO XML (signed acknowledgment from MF — keep for audits)
    base = f"invoice_{invoice.invoice_number}_{year}"
    if result.upo_xml:
        upo_path = OUTPUT_DIR / f"{base}.upo.xml"
        upo_path.write_bytes(result.upo_xml)
        typer.echo(f"UPO saved: {upo_path}")

    # Save KSeF submission metadata sidecar
    metadata = {
        "invoice_number": f"{invoice.invoice_number}/{year}",
        "ksef_number": result.ksef_number,
        "reference_number": result.reference_number,
        "env": result.env,
        "submitted_at": result.submitted_at,
        "status_code": result.status_code,
        "status_description": result.status_description,
        "upo_url": result.upo_url,
    }
    (OUTPUT_DIR / f"{base}.ksef.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False)
    )

    # Regenerate PDF with KSeF QR code
    if result.ksef_number:
        from .core.pdf_generator import generate_pdf

        pdf_path = OUTPUT_DIR / f"{base}.pdf"
        generate_pdf(
            invoice=invoice,
            seller=config["seller"],
            buyer=config["buyer"],
            output_path=str(pdf_path),
            ksef_number=result.ksef_number,
            invoice_xml=xml_bytes,
            ksef_env=env,
        )
        typer.echo(f"PDF with QR code: {pdf_path}")

    # Auto-backup after production submit
    backup_cfg = config.get("backup") or {}
    if env == "prod" and backup_cfg.get("auto_after_prod_submit"):
        from .core.backup import backup_month

        try:
            dest = backup_month(month, config)
            if dest:
                typer.echo(f"Backed up to: {dest}")
        except (FileNotFoundError, OSError) as e:
            typer.echo(f"⚠ Backup skipped: {e}")


@app.command("download-upo")
def cmd_download_upo(
    month: str = typer.Argument(help="Month in YYYY-MM format"),
    env: str = typer.Option("prod", help="KSeF environment: test, demo, prod"),
):
    """Download UPO (signed acknowledgment) for a previously submitted invoice."""
    from .core.ksef_client_wrapper import download_upo

    entry = get_or_create_month(month)
    if not entry.ksef_id:
        typer.echo(f"No KSeF ID stored for {month} — was it submitted?")
        raise typer.Exit(1)

    invoice = calculate_invoice(entry)
    year = month[:4]
    base = f"invoice_{invoice.invoice_number}_{year}"

    typer.echo(f"Fetching UPO from KSeF ({env}) for {entry.ksef_id}...")
    upo_xml = download_upo(ksef_number=entry.ksef_id, env=env)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    upo_path = OUTPUT_DIR / f"{base}.upo.xml"
    upo_path.write_bytes(upo_xml)
    typer.echo(f"UPO saved: {upo_path}")

    ksef_json_path = OUTPUT_DIR / f"{base}.ksef.json"
    if not ksef_json_path.exists():
        ksef_json_path.write_text(
            json.dumps(
                {
                    "invoice_number": f"{invoice.invoice_number}/{year}",
                    "ksef_number": entry.ksef_id,
                    "env": env,
                    "note": "Backfilled — submission metadata not preserved",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        typer.echo(f"ksef.json (partial): {ksef_json_path}")


@app.command()
def backup(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Copy invoice artifacts (PDF, XML, UPO, YAML, ksef.json) to backup directory."""
    from .core.backup import backup_month

    config = load_config()
    if not (config.get("backup") or {}).get("enabled"):
        typer.echo("Backup is disabled in config.yaml (backup.enabled = false).")
        raise typer.Exit(1)

    dest = backup_month(month, config)
    typer.echo(f"Backed up to: {dest}")
    for f in sorted(dest.iterdir()):
        typer.echo(f"  - {f.name}")


_MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@app.command()
def send(
    month: str = typer.Argument(help="Month in YYYY-MM format"),
    open_compose: bool = typer.Option(
        False, "--open", help="Open Outlook Web compose with prefilled fields"
    ),
):
    """Print the email template for sending the invoice (and optionally open Outlook Web)."""
    from urllib.parse import quote

    config = load_config()
    email_cfg = config.get("email") or {}
    recipient = email_cfg.get("recipient")
    if not recipient:
        typer.echo("No email.recipient configured in config.yaml.")
        raise typer.Exit(1)

    entry = get_or_create_month(month)
    invoice = calculate_invoice(entry)
    year = month[:4]
    month_name = _MONTH_NAMES_EN[int(month[5:7]) - 1]

    subject = email_cfg.get(
        "subject_template",
        "invoice {invoice_number}/{year} for {month_name} {year}",
    ).format(invoice_number=invoice.invoice_number, year=year, month_name=month_name)

    pdf_path = OUTPUT_DIR / f"invoice_{invoice.invoice_number}_{year}.pdf"

    typer.echo(f"\n{'=' * 50}")
    typer.echo(f"  Email template for invoice {invoice.invoice_number}/{year}")
    typer.echo(f"{'=' * 50}")
    typer.echo(f"  To:      {recipient}")
    typer.echo(f"  Title:   {subject}")
    typer.echo(f"  Content: (empty)")
    typer.echo(f"  Attach:  {pdf_path}")
    typer.echo(f"{'=' * 50}\n")

    if open_compose:
        url = (
            "https://outlook.office.com/mail/deeplink/compose"
            f"?to={quote(recipient)}&subject={quote(subject)}"
        )
        typer.echo(f"Opening Outlook Web compose...")
        if sys.platform == "darwin":
            subprocess.run(["open", url])
        elif sys.platform == "linux":
            subprocess.run(["xdg-open", url])
        typer.echo("Drag the PDF from Finder into the compose window to attach.")


@app.command()
def status(month: str = typer.Argument(help="Month in YYYY-MM format")):
    """Check KSeF status for an invoice."""
    entry = get_or_create_month(month)
    typer.echo(f"Invoice {entry.invoice_number}/{month[:4]}")
    typer.echo(f"  Status: {entry.status}")
    typer.echo(f"  KSeF ID: {entry.ksef_id or 'not submitted'}")


if __name__ == "__main__":
    app()
