"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vntax.io_jsonl import (
    dump_findings,
    dump_invoices,
    finding_from_dict,
    invoice_from_dict,
    load_findings,
    load_invoices,
)
from vntax.validator import Finding, Severity

from ._fixtures import make_invoice


def test_invoice_roundtrip():
    inv = make_invoice()
    [back] = list(load_invoices(dump_invoices([inv])))
    assert back == inv


def test_finding_roundtrip():
    f = Finding(invoice_id="INV-1", severity=Severity.ERROR, code="LINE_TOTAL_MISMATCH", detail="x")
    [back] = list(load_findings(dump_findings([f])))
    assert back == f


def test_invoice_decoder_rejects_unknown_kind():
    bad = {
        "invoice_id": "INV",
        "serial": "K",
        "template_code": "1/001",
        "invoice_number": 1,
        "kind": "WEIRD",
        "seller_tax_code": "0100109106",
        "seller_name": "S",
        "buyer_tax_code": None,
        "buyer_name": None,
        "issued_at": "2026-05-14T09:00:00+07:00",
        "items": [],
        "subtotal_vnd": 0,
        "vat_total_vnd": 0,
        "grand_total_vnd": 0,
    }
    with pytest.raises(ValueError):
        invoice_from_dict(bad)


def test_finding_decoder_rejects_unknown_severity():
    bad = {"invoice_id": "INV", "severity": "FATAL", "code": "X", "detail": "y"}
    with pytest.raises(ValueError):
        finding_from_dict(bad)


def test_invoice_decoder_rejects_bool_for_int():
    bad = {
        "invoice_id": "INV",
        "serial": "K",
        "template_code": "1/001",
        "invoice_number": True,
        "kind": "VAT_INVOICE",
        "seller_tax_code": "0100109106",
        "seller_name": "S",
        "buyer_tax_code": None,
        "buyer_name": None,
        "issued_at": "2026-05-14T09:00:00+07:00",
        "items": [],
        "subtotal_vnd": 0,
        "vat_total_vnd": 0,
        "grand_total_vnd": 0,
    }
    with pytest.raises(TypeError, match="invoice_number"):
        invoice_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_invoices([make_invoice()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_invoices(padded))) == 1


def test_multi_invoice_roundtrip():
    invoices = [make_invoice(invoice_id=f"INV-{i:03d}", invoice_number=i + 1) for i in range(5)]
    text = dump_invoices(invoices)
    assert list(load_invoices(text)) == invoices


def test_currency_defaults_to_vnd_when_missing():
    """The encoder always writes currency, but a hand-crafted JSON without
    it should still decode (defensive)."""
    text = dump_invoices([make_invoice()])
    import json

    payload = json.loads(text.strip().split("\n")[0])
    del payload["currency"]
    inv = invoice_from_dict(payload)
    assert inv.currency == "VND"
