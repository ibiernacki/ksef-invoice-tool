"""Tests for KSeF FA(3) XML generation."""

import subprocess
from datetime import date
from decimal import Decimal

from lxml import etree

from src.core.ksef_xml import generate_invoice_xml
from src.core.models import InvoiceData

FA3_NS = "http://crd.gov.pl/wzor/2025/06/25/13775/"


def _make_invoice(**overrides) -> InvoiceData:
    defaults = dict(
        month="2026-04",
        invoice_number="0004",
        issued_date=date(2026, 4, 30),
        selling_date=date(2026, 4, 30),
        payment_deadline=date(2026, 5, 7),
        ref_person="Anna Svensson",
        days_worked=21,
        days_total=21,
        base_salary=Decimal("20000"),
        work_salary=Decimal("20000"),
        expenses_total=Decimal("0"),
        additional_gross=Decimal("0"),
        final_amount=Decimal("20000"),
        multiplier=Decimal("1"),
        net_value=Decimal("20000"),
    )
    defaults.update(overrides)
    return InvoiceData(**defaults)


SELLER = {
    "name": "Jan Kowalski",
    "nip": "PL1111111111",
    "address": "ul. Przykładowa 1/2, 00-001 Warszawa, Poland",
    "bank_account": "PL61109010140000071219812874",
    "bic": "BREXPLPW",
}

BUYER = {
    "name": "Example Client AB",
    "reg_number": "556000-0000",
    "vat_id": "SE556000000001",
    "address": "Kungsgatan 1, 111 43 Stockholm, Sweden",
}


def test_xml_is_well_formed():
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)
    doc = etree.fromstring(xml)
    assert doc.tag == f"{{{FA3_NS}}}Faktura"


def test_xml_contains_seller_nip():
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)
    doc = etree.fromstring(xml)
    nip = doc.find(f".//{{{FA3_NS}}}Podmiot1/{{{FA3_NS}}}DaneIdentyfikacyjne/{{{FA3_NS}}}NIP")
    assert nip.text == "1111111111"


def test_xml_contains_buyer_eu_vat():
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)
    doc = etree.fromstring(xml)
    kod_ue = doc.find(
        f".//{{{FA3_NS}}}Podmiot2/{{{FA3_NS}}}DaneIdentyfikacyjne/{{{FA3_NS}}}KodUE"
    )
    nr_vat = doc.find(
        f".//{{{FA3_NS}}}Podmiot2/{{{FA3_NS}}}DaneIdentyfikacyjne/{{{FA3_NS}}}NrVatUE"
    )
    assert kod_ue.text == "SE"
    assert nr_vat.text == "556000000001"


def test_xml_reverse_charge_fields():
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)
    doc = etree.fromstring(xml)

    # P_12 should be "np I" for intracommunity reverse charge
    p12 = doc.find(f".//{{{FA3_NS}}}FaWiersz/{{{FA3_NS}}}P_12")
    assert p12.text == "np I"

    # P_18A should be 1 (intracommunity)
    p18a = doc.find(f".//{{{FA3_NS}}}Adnotacje/{{{FA3_NS}}}P_18A")
    assert p18a.text == "1"

    # P_13_11 should contain net value
    p13_11 = doc.find(f".//{{{FA3_NS}}}Fa/{{{FA3_NS}}}P_13_11")
    assert p13_11.text == "20000.00"


def test_xml_invoice_number_format():
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)
    doc = etree.fromstring(xml)
    p2 = doc.find(f".//{{{FA3_NS}}}Fa/{{{FA3_NS}}}P_2")
    assert p2.text == "0004/2026"


def test_xml_passes_ksefuj_validator(tmp_path):
    """Integration test: validate XML with @ksefuj/validator (requires npx)."""
    invoice = _make_invoice()
    xml = generate_invoice_xml(invoice, SELLER, BUYER)

    xml_file = tmp_path / "test_invoice.xml"
    xml_file.write_bytes(xml)

    result = subprocess.run(
        ["npx", "@ksefuj/validator", str(xml_file)],
        capture_output=True,
    )
    assert result.returncode == 0, f"Validator failed:\n{result.stderr.decode()}\n{result.stdout.decode()}"
