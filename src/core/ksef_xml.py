"""KSeF FA(3) XML invoice generator."""

from lxml import etree

from .models import InvoiceData

# FA(3) namespace
FA3_NS = "http://crd.gov.pl/wzor/2025/06/25/13775/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NSMAP = {
    None: FA3_NS,
    "xsi": XSI_NS,
}


def _el(parent: etree._Element, tag: str, text: str | None = None) -> etree._Element:
    """Create a child element with optional text."""
    elem = etree.SubElement(parent, tag)
    if text is not None:
        elem.text = str(text)
    return elem


def generate_invoice_xml(
    invoice: InvoiceData,
    seller: dict,
    buyer: dict,
) -> bytes:
    """Generate FA(3) XML for KSeF submission.

    Returns UTF-8 encoded XML bytes.
    """
    root = etree.Element("Faktura", nsmap=NSMAP)
    root.set(
        f"{{{XSI_NS}}}schemaLocation",
        f"{FA3_NS} http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd",
    )

    # ── Naglowek (Header) ──────────────────────────────
    naglowek = _el(root, "Naglowek")
    kod = _el(naglowek, "KodFormularza", "FA")
    kod.set("kodSystemowy", "FA (3)")
    kod.set("wersjaSchemy", "1-0E")
    _el(naglowek, "WariantFormularza", "3")
    _el(
        naglowek,
        "DataWytworzeniaFa",
        invoice.issued_date.isoformat() + "T00:00:00",
    )
    _el(naglowek, "SystemInfo", "invoice-tool")

    # ── Podmiot1 (Seller) ──────────────────────────────
    podmiot1 = _el(root, "Podmiot1")

    dane1 = _el(podmiot1, "DaneIdentyfikacyjne")
    nip = seller["nip"].replace("PL", "")
    _el(dane1, "NIP", nip)
    _el(dane1, "Nazwa", seller["name"])

    adres1 = _el(podmiot1, "Adres")
    _el(adres1, "KodKraju", "PL")
    _el(adres1, "AdresL1", seller["address"])

    # ── Podmiot2 (Buyer) ───────────────────────────────
    podmiot2 = _el(root, "Podmiot2")

    dane2 = _el(podmiot2, "DaneIdentyfikacyjne")
    vat_id = buyer["vat_id"]
    kod_ue = vat_id[:2]  # "SE"
    nr_vat = vat_id[2:]  # "556000000001"
    _el(dane2, "KodUE", kod_ue)
    _el(dane2, "NrVatUE", nr_vat)
    # Nazwa must be inside DaneIdentyfikacyjne for foreign buyers
    _el(dane2, "Nazwa", buyer["name"])

    adres2 = _el(podmiot2, "Adres")
    _el(adres2, "KodKraju", kod_ue)
    _el(adres2, "AdresL1", buyer["address"])

    # Required flags
    _el(podmiot2, "JST", "2")  # Not a local government unit
    _el(podmiot2, "GV", "2")  # Not a VAT group member

    # ── Fa (Invoice data) ──────────────────────────────
    fa = _el(root, "Fa")
    _el(fa, "KodWaluty", "PLN")
    _el(fa, "P_1", invoice.issued_date.isoformat())  # Issue date
    _el(fa, "P_2", f"{invoice.invoice_number}/{invoice.month[:4]}")  # Invoice number
    _el(fa, "P_6", invoice.selling_date.isoformat())  # Selling date

    # P_13_9: net value for intra-EU services to a VAT-registered buyer (art. 100 ust. 1 pkt 4) — matches P_12 "np I"
    _el(fa, "P_13_9", f"{float(invoice.net_value):.2f}")

    # Total net value
    _el(fa, "P_15", f"{float(invoice.net_value):.2f}")

    # Adnotacje MUST come before FaWiersz
    adnotacje = _el(fa, "Adnotacje")
    _el(adnotacje, "P_16", "2")  # No metoda kasowa
    _el(adnotacje, "P_17", "2")  # No samofakturowanie
    _el(adnotacje, "P_18", "2")  # No "odwrotne obciążenie" annotation (EU reverse charge expressed via P_12=np I + Podmiot2/KodUE)
    _el(adnotacje, "P_18A", "2")  # No MPP — software dev not in załącznik 15 + EU transaction
    zwolnienie = _el(adnotacje, "Zwolnienie")
    _el(zwolnienie, "P_19N", "1")  # Not exempt
    nst = _el(adnotacje, "NoweSrodkiTransportu")
    _el(nst, "P_22N", "1")  # 1 = not new means of transport
    _el(adnotacje, "P_23", "2")  # Not a simplified invoice
    pmarzy = _el(adnotacje, "PMarzy")
    _el(pmarzy, "P_PMarzyN", "1")  # 1 = not margin procedure

    # RodzajFaktury is required after Adnotacje
    _el(fa, "RodzajFaktury", "VAT")

    # Line items (after RodzajFaktury)
    fa_wiersz = _el(fa, "FaWiersz")
    _el(fa_wiersz, "NrWierszaFa", "1")
    _el(fa_wiersz, "P_7", "Software development services")  # Description
    _el(fa_wiersz, "P_8A", "month")  # Unit
    _el(fa_wiersz, "P_8B", f"{float(invoice.multiplier):.6f}")  # Quantity
    _el(fa_wiersz, "P_9A", f"{float(invoice.base_salary):.2f}")  # Unit price
    _el(fa_wiersz, "P_11", f"{float(invoice.net_value):.2f}")  # Net value
    _el(fa_wiersz, "P_12", "np I")  # VAT rate: "np I" = nie podlega intracommunity

    # Payment info — elements directly under Platnosc
    platnosc = _el(fa, "Platnosc")
    termin = _el(platnosc, "TerminPlatnosci")
    _el(termin, "Termin", invoice.payment_deadline.isoformat())
    _el(platnosc, "FormaPlatnosci", "6")  # 6 = bank transfer
    rachunek = _el(platnosc, "RachunekBankowy")
    _el(rachunek, "NrRB", seller["bank_account"].replace(" ", ""))
    _el(rachunek, "SWIFT", seller["bic"])
    if seller.get("bank_name"):
        _el(rachunek, "NazwaBanku", seller["bank_name"])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def validate_xml_offline(xml_bytes: bytes, xsd_path: str | None = None) -> list[str]:
    """Validate XML against FA(3) XSD schema.

    Returns list of error messages (empty = valid).
    If xsd_path is None, only checks well-formedness.
    """
    errors = []

    try:
        doc = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        return [f"XML syntax error: {e}"]

    if xsd_path:
        try:
            with open(xsd_path, "rb") as f:
                schema_doc = etree.parse(f)
            schema = etree.XMLSchema(schema_doc)
            if not schema.validate(doc):
                errors = [str(e) for e in schema.error_log]
        except Exception as e:
            errors = [f"Schema validation error: {e}"]

    return errors
