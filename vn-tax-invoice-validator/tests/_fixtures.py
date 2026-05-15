"""Canonical invoice builders for tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vntax.schema import VN_TZ, Invoice, InvoiceItem, InvoiceKind, TaxCode, VATRate

DEFAULT_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


def make_item(**overrides: Any) -> InvoiceItem:
    defaults = {
        "line_no": 1,
        "description": "Hàng hoá dòng 1",
        "quantity": 2,
        "unit_price_vnd": 500_000,
        "vat_rate": VATRate.TEN,
        "line_total_vnd": 1_000_000,  # 2 × 500_000
        "vat_amount_vnd": 100_000,  # 1M × 10%
    }
    defaults.update(overrides)
    return InvoiceItem(**defaults)  # type: ignore[arg-type]


def make_invoice(items: list[InvoiceItem] | None = None, **overrides: Any) -> Invoice:
    actual_items = tuple(items) if items is not None else (make_item(),)
    subtotal = sum(i.line_total_vnd for i in actual_items)
    vat_total = sum(i.vat_amount_vnd for i in actual_items)
    defaults = {
        "invoice_id": "INV-0001",
        "serial": "K22TAA",
        "template_code": "1/001",
        "invoice_number": 1,
        "kind": InvoiceKind.VAT_INVOICE,
        "seller_tax_code": TaxCode(digits="0100109106"),  # Vietcombank (real)
        "seller_name": "Vietcombank",
        "buyer_tax_code": TaxCode(digits="0301442379"),  # FPT (real)
        "buyer_name": "FPT Corp",
        "issued_at": DEFAULT_TS,
        "items": actual_items,
        "subtotal_vnd": subtotal,
        "vat_total_vnd": vat_total,
        "grand_total_vnd": subtotal + vat_total,
        "currency": "VND",
    }
    defaults.update(overrides)
    return Invoice(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_invoice", "make_item"]
