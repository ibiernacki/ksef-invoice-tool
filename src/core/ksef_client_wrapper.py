"""KSeF API client wrapper using ksef2 library."""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# KSeF query_metadata caps date range at 3 calendar months. 85 days is safely under.
KSEF_QUERY_WINDOW_DAYS = 85


@dataclass
class KsefSubmitResult:
    reference_number: str
    ksef_number: str | None = None
    invoice_number: str | None = None
    status_code: int | None = None
    status_description: str | None = None
    upo_url: str | None = None
    upo_xml: bytes | None = None
    submitted_at: str | None = None
    env: str | None = None


def _get_nip() -> str:
    from .store import load_config

    return load_config()["seller"]["nip"].replace("PL", "")


def _get_token(var: str = "KSEF_TOKEN") -> str:
    token = os.environ.get(var)
    if not token:
        raise ValueError(f"{var} not found in .env file")
    return token


def _build_auth(env: str, token_var: str = "KSEF_TOKEN"):
    from ksef2 import Client, Environment

    env_map = {
        "test": Environment.TEST,
        "demo": Environment.DEMO,
        "prod": Environment.PRODUCTION,
    }
    if env not in env_map:
        raise ValueError(f"Unknown environment: {env}. Use: test, demo, prod")

    nip = _get_nip()
    client = Client(env_map[env])
    if env == "test":
        return client.authentication.with_test_certificate(nip=nip)
    return client.authentication.with_token(ksef_token=_get_token(token_var), nip=nip)


def download_upo(ksef_number: str, env: str = "prod") -> bytes:
    """Fetch UPO XML for a previously submitted invoice.

    UPO is session-scoped in KSeF — we walk the online-session history,
    find the session that submitted the given ksef_number, and fetch UPO
    via that session's reference.
    """
    from ksef2.endpoints.invoices import InvoicesEndpoints

    auth = _build_auth(env)
    endpoints = InvoicesEndpoints(auth.invoices._transport)

    last_error: Exception | None = None
    for page in auth.invoice_sessions.all(session_type="online"):
        for session in (page.sessions or []):
            ref = getattr(session, "reference_number", None)
            status = getattr(session, "status", None)
            if not ref or not status or status.code != 200:
                continue
            try:
                return endpoints.get_invoice_upo_by_ksef(
                    reference_number=ref,
                    ksef_number=ksef_number,
                )
            except Exception as e:
                last_error = e
                continue

    raise RuntimeError(
        f"UPO not found in any session history for {ksef_number}. "
        f"Last error: {last_error}"
    )


def submit_invoice(invoice_xml: bytes, env: str = "test") -> KsefSubmitResult:
    """Submit an invoice to KSeF.

    Args:
        invoice_xml: FA(3) XML bytes
        env: Environment (test, demo, prod)
    """
    from ksef2 import FormSchema

    auth = _build_auth(env)

    with auth.online_session(form_code=FormSchema.FA3) as session:
        result = session.send_invoice(invoice_xml=invoice_xml)
        status = session.wait_for_invoice_ready(
            invoice_reference_number=result.reference_number
        )

        upo_xml: bytes | None = None
        if status.ksef_number:
            try:
                upo_xml = session.get_invoice_upo_by_ksef_number(ksef_number=status.ksef_number)
            except Exception:
                # UPO retrieval is best-effort — submission already succeeded
                upo_xml = None

        return KsefSubmitResult(
            reference_number=status.reference_number,
            ksef_number=status.ksef_number,
            invoice_number=status.invoice_number,
            status_code=status.status.code,
            status_description=status.status.description,
            upo_url=str(status.upo_download_url) if status.upo_download_url else None,
            upo_xml=upo_xml,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            env=env,
        )


def list_invoices(
    *,
    role: str = "buyer",
    date_from: datetime,
    date_to: datetime | None = None,
    date_type: str = "invoicing_date",
    amount_type: str = "brutto",
    page_size: int = 100,
    sort_order: str = "desc",
    env: str = "prod",
):
    """List invoice metadata from KSeF.

    Uses the read-only KSEF_READ_INVOICES_TOKEN. Handles pagination and
    chunks date windows >85 days into multiple calls (the API caps a single
    query at ~3 calendar months).

    Returns a deduplicated list of `InvoiceMetadata` ordered by
    `invoicing_date` according to `sort_order`.
    """
    from ksef2.domain.models.invoices import InvoicesFilter
    from ksef2.domain.models.pagination import InvoiceMetadataParams

    if date_to is None:
        date_to = datetime.now(timezone.utc)
    if date_from.tzinfo is None:
        date_from = date_from.replace(tzinfo=timezone.utc)
    if date_to.tzinfo is None:
        date_to = date_to.replace(tzinfo=timezone.utc)
    if date_from >= date_to:
        return []

    auth = _build_auth(env, token_var="KSEF_READ_INVOICES_TOKEN")

    seen: dict[str, object] = {}
    chunk_start = date_from
    while chunk_start < date_to:
        chunk_end = min(
            chunk_start + timedelta(days=KSEF_QUERY_WINDOW_DAYS), date_to
        )
        page_offset = 0
        while True:
            filters = InvoicesFilter(
                role=role,
                date_type=date_type,
                date_from=chunk_start.isoformat(),
                date_to=chunk_end.isoformat(),
                amount_type=amount_type,
            )
            params = InvoiceMetadataParams(
                page_size=page_size,
                page_offset=page_offset,
                sort_order=sort_order,
            )
            resp = auth.invoices.query_metadata(filters=filters, params=params)
            for inv in resp.invoices:
                seen[inv.ksef_number] = inv
            if not resp.has_more:
                break
            page_offset += 1
        chunk_start = chunk_end

    return sorted(
        seen.values(),
        key=lambda i: i.invoicing_date,
        reverse=(sort_order == "desc"),
    )


def download_invoice_xml(ksef_number: str, env: str = "prod") -> bytes:
    """Download FA(3) XML by KSeF number using the read-only token."""
    auth = _build_auth(env, token_var="KSEF_READ_INVOICES_TOKEN")
    return auth.invoices.download_invoice(ksef_number=ksef_number)
