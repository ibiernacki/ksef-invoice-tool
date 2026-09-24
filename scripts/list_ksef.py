"""List invoices from KSeF (read-only).

Designed to be both interactive and machine-callable. Use --json for
automation (e.g. a routine that detects new purchase invoices).

Examples:
    uv run python scripts/list_ksef.py
    uv run python scripts/list_ksef.py --role seller
    uv run python scripts/list_ksef.py --days 90
    uv run python scripts/list_ksef.py --from 2026-01-01 --to 2026-04-30
    uv run python scripts/list_ksef.py --json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from src.core.ksef_client_wrapper import list_invoices


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _to_dict(inv) -> dict:
    return {
        "ksef_number": inv.ksef_number,
        "invoice_number": inv.invoice_number,
        "issue_date": inv.issue_date.isoformat(),
        "invoicing_date": inv.invoicing_date.isoformat(),
        "permanent_storage_date": inv.permanent_storage_date.isoformat(),
        "seller_nip": inv.seller.nip,
        "seller_name": inv.seller.name,
        "buyer_id": inv.buyer.identifier.value,
        "buyer_name": inv.buyer.name,
        "net_amount": inv.net_amount,
        "gross_amount": inv.gross_amount,
        "vat_amount": inv.vat_amount,
        "currency": inv.currency,
        "invoice_type": str(inv.invoice_type),
        "has_attachment": inv.has_attachment,
    }


def _print_text(invoices, role: str) -> None:
    if not invoices:
        print(f"No {role} invoices in the requested period.")
        return
    label = "from" if role == "buyer" else "to"
    print(f"{len(invoices)} {role} invoice(s):\n")
    net_total = vat_total = gross_total = 0.0
    currency = None
    for inv in invoices:
        if role == "buyer":
            party = f"{inv.seller.nip} {inv.seller.name or ''}".strip()
        else:
            party = f"{inv.buyer.identifier.value} {inv.buyer.name or ''}".strip()
        print(
            f"  {inv.invoicing_date.date()}  "
            f"{inv.invoice_number:<28}  "
            f"net {inv.net_amount:>9.2f}  vat {inv.vat_amount:>8.2f}  "
            f"gross {inv.gross_amount:>9.2f} {inv.currency}  "
            f"{label} {party}"
        )
        print(f"      ksef: {inv.ksef_number}")
        net_total += inv.net_amount
        vat_total += inv.vat_amount
        gross_total += inv.gross_amount
        currency = inv.currency

    if len(invoices) > 1:
        print(
            f"\n  Total ({len(invoices)}):  "
            f"net {net_total:>9.2f}  vat {vat_total:>8.2f}  "
            f"gross {gross_total:>9.2f} {currency}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--role",
        choices=["seller", "buyer", "third_subject", "authorized_subject"],
        default="buyer",
        help="seller=invoices we issued, buyer=invoices we received (default)",
    )
    parser.add_argument("--from", dest="date_from", type=_parse_date)
    parser.add_argument("--to", dest="date_to", type=_parse_date)
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Lookback window in days when --from is not given (default 30)",
    )
    parser.add_argument(
        "--date-type",
        choices=["issue_date", "invoicing_date", "permanent_storage"],
        default="invoicing_date",
    )
    parser.add_argument(
        "--sort", choices=["asc", "desc"], default="desc",
        help="Sort by invoicing_date (default desc=newest first)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON (use for automation)"
    )
    args = parser.parse_args()

    if args.date_from is None:
        args.date_from = datetime.now(timezone.utc) - timedelta(days=args.days)

    invoices = list_invoices(
        role=args.role,
        date_from=args.date_from,
        date_to=args.date_to,
        date_type=args.date_type,
        sort_order=args.sort,
    )

    if args.json:
        json.dump(
            [_to_dict(i) for i in invoices], sys.stdout, indent=2, ensure_ascii=False
        )
        sys.stdout.write("\n")
    else:
        _print_text(invoices, args.role)


if __name__ == "__main__":
    main()
