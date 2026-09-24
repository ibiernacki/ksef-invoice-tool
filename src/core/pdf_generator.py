"""PDF invoice generator using WeasyPrint + Jinja2."""

import base64
import io
import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import InvoiceData

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _format_date(d) -> str:
    """Format date as DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y")


def _format_amount(amount) -> str:
    """Format amount with 2 decimal places."""
    return f"{float(amount):.2f}"


def _format_multiplier(multiplier) -> str:
    """Format multiplier with 3 decimal places."""
    return f"{float(multiplier):.3f}"


QR_BASE_URLS = {
    "test": "https://qr-test.ksef.mf.gov.pl",
    "demo": "https://qr-demo.ksef.mf.gov.pl",
    "prod": "https://qr.ksef.mf.gov.pl",
}


def generate_ksef_qr_url(
    seller_nip: str,
    issued_date,
    invoice_xml_hash: str,
    env: str = "prod",
) -> str:
    """Build KSeF 2.0 QR Code I verification URL.

    Format: {base}/invoice/{NIP}/{DD-MM-RRRR}/{SHA256_BASE64URL}
    """
    base = QR_BASE_URLS.get(env, QR_BASE_URLS["prod"])
    nip = seller_nip.replace("PL", "")
    date_str = issued_date.strftime("%d-%m-%Y")
    return f"{base}/invoice/{nip}/{date_str}/{invoice_xml_hash}"


def compute_invoice_hash(invoice_xml: bytes) -> str:
    """Compute SHA-256 hash of invoice XML, Base64URL encoded."""
    import hashlib

    digest = hashlib.sha256(invoice_xml).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def generate_qr_data_uri(qr_url: str) -> str:
    """Generate a QR code as a base64 data URI for embedding in HTML."""
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def generate_pdf(
    invoice: InvoiceData,
    seller: dict,
    buyer: dict,
    output_path: str,
    ksef_number: str | None = None,
    invoice_xml: bytes | None = None,
    ksef_env: str = "prod",
) -> str:
    """Generate a PDF invoice and return the output path.

    If ksef_number and invoice_xml are provided, generates a QR code
    using the KSeF 2.0 Code I format.
    """
    jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = jinja_env.get_template("invoice.html")

    # Generate QR code if KSeF data available
    qr_data_uri = None
    if ksef_number and invoice_xml:
        xml_hash = compute_invoice_hash(invoice_xml)
        nip = seller["nip"].replace("PL", "")
        qr_url = generate_ksef_qr_url(nip, invoice.issued_date, xml_hash, env=ksef_env)
        qr_data_uri = generate_qr_data_uri(qr_url)

    html_content = template.render(
        # Invoice metadata
        invoice_number=invoice.invoice_number,
        year=invoice.month[:4],
        issued_date=_format_date(invoice.issued_date),
        selling_date=_format_date(invoice.selling_date),
        payment_deadline=_format_date(invoice.payment_deadline),
        ref_person=invoice.ref_person,
        # Parties
        seller=seller,
        buyer=buyer,
        # Line item
        service_description="Software development services",
        unit="month",
        multiplier=_format_multiplier(invoice.multiplier),
        base_salary=_format_amount(invoice.base_salary),
        net_value=_format_amount(invoice.net_value),
        vat_type="NP",
        currency="PLN",
        # KSeF
        qr_code=qr_data_uri,
        ksef_number=ksef_number,
    )

    # Ensure homebrew libs are findable on macOS
    if sys.platform == "darwin":
        homebrew_lib = "/opt/homebrew/lib"
        fallback = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if homebrew_lib not in fallback:
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{homebrew_lib}:{fallback}".rstrip(":")

    from weasyprint import HTML

    html = HTML(string=html_content, base_url=str(TEMPLATES_DIR))
    html.write_pdf(output_path)
    return output_path
