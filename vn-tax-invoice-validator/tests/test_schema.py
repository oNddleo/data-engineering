"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from vntax.schema import VN_TZ, InvoiceKind, TaxCode, VATRate

from ._fixtures import DEFAULT_TS, make_invoice, make_item


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_vat_rate_basis_points():
    assert VATRate.ZERO.value == 0
    assert VATRate.FIVE.value == 500
    assert VATRate.EIGHT.value == 800
    assert VATRate.TEN.value == 1000


def test_invoice_kind_enum_has_three_values():
    assert {k.value for k in InvoiceKind} == {"VAT_INVOICE", "SALES_INVOICE", "EXPORT_INVOICE"}


def test_tax_code_rejects_non_digits():
    with pytest.raises(ValueError):
        TaxCode(digits="01001091A6")


def test_tax_code_rejects_wrong_length():
    with pytest.raises(ValueError):
        TaxCode(digits="123")
    with pytest.raises(ValueError):
        TaxCode(digits="12345678901")  # 11 — illegal length


def test_tax_code_branch_suffix_property():
    full = TaxCode(digits="0301442379001")
    assert full.primary == "0301442379"
    assert full.branch_suffix == "001"
    primary_only = TaxCode(digits="0100109106")
    assert primary_only.primary == "0100109106"
    assert primary_only.branch_suffix is None


def test_invoice_item_rejects_zero_quantity():
    with pytest.raises(ValueError):
        make_item(quantity=0)


def test_invoice_item_rejects_negative_unit_price():
    with pytest.raises(ValueError):
        make_item(unit_price_vnd=-1)


def test_invoice_item_rejects_negative_vat():
    with pytest.raises(ValueError):
        make_item(vat_amount_vnd=-1)


def test_invoice_item_rejects_empty_description():
    with pytest.raises(ValueError):
        make_item(description="")


def test_invoice_rejects_no_items():
    with pytest.raises(ValueError, match="at least one item"):
        make_invoice(items=[])


def test_invoice_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_invoice(issued_at=datetime(2026, 5, 14))


def test_invoice_rejects_non_vnd_currency():
    with pytest.raises(ValueError):
        make_invoice(currency="USD")


def test_invoice_rejects_gapped_line_numbers():
    items = [make_item(line_no=1), make_item(line_no=3)]
    with pytest.raises(ValueError, match="contiguous"):
        make_invoice(items=items)


def test_invoice_rejects_negative_totals():
    """All three totals are validated >= 0."""
    with pytest.raises(ValueError):
        make_invoice(subtotal_vnd=-1)


def test_invoice_accepts_no_buyer_for_b2c():
    """Retail VAT invoice can have no buyer MST."""
    inv = make_invoice(buyer_tax_code=None, buyer_name=None)
    assert inv.buyer_tax_code is None


def test_invoice_rejects_empty_serial():
    with pytest.raises(ValueError):
        make_invoice(serial="")


def test_invoice_rejects_zero_invoice_number():
    with pytest.raises(ValueError):
        make_invoice(invoice_number=0)


def test_default_invoice_passes_validation_at_construction():
    """The fixture builds a legal default invoice."""
    inv = make_invoice()
    assert inv.invoice_id == "INV-0001"
    assert inv.issued_at == DEFAULT_TS
