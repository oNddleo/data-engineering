"""Type-checked JSONL codec for Invoice + Finding."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vntax.schema import Invoice, InvoiceItem, InvoiceKind, TaxCode, VATRate
from vntax.validator import Finding, Severity

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def _item_to_dict(i: InvoiceItem) -> dict[str, object]:
    return {
        "line_no": i.line_no,
        "description": i.description,
        "quantity": i.quantity,
        "unit_price_vnd": i.unit_price_vnd,
        "vat_rate": i.vat_rate.name,
        "line_total_vnd": i.line_total_vnd,
        "vat_amount_vnd": i.vat_amount_vnd,
    }


def _item_from_dict(d: dict[str, object]) -> InvoiceItem:
    return InvoiceItem(
        line_no=_require_int(d, "line_no"),
        description=_require_str(d, "description"),
        quantity=_require_int(d, "quantity"),
        unit_price_vnd=_require_int(d, "unit_price_vnd"),
        vat_rate=VATRate[_require_str(d, "vat_rate")],
        line_total_vnd=_require_int(d, "line_total_vnd"),
        vat_amount_vnd=_require_int(d, "vat_amount_vnd"),
    )


def invoice_to_dict(inv: Invoice) -> dict[str, object]:
    return {
        "invoice_id": inv.invoice_id,
        "serial": inv.serial,
        "template_code": inv.template_code,
        "invoice_number": inv.invoice_number,
        "kind": inv.kind.value,
        "seller_tax_code": inv.seller_tax_code.digits,
        "seller_name": inv.seller_name,
        "buyer_tax_code": inv.buyer_tax_code.digits if inv.buyer_tax_code else None,
        "buyer_name": inv.buyer_name,
        "issued_at": inv.issued_at.isoformat(),
        "items": [_item_to_dict(i) for i in inv.items],
        "subtotal_vnd": inv.subtotal_vnd,
        "vat_total_vnd": inv.vat_total_vnd,
        "grand_total_vnd": inv.grand_total_vnd,
        "currency": inv.currency,
    }


def invoice_from_dict(d: dict[str, object]) -> Invoice:
    raw_items = d["items"]
    if not isinstance(raw_items, list):
        raise TypeError("items must be a list")
    items = tuple(_item_from_dict(it) for it in raw_items if isinstance(it, dict))
    buyer_mst_raw = _optional_str(d, "buyer_tax_code")
    return Invoice(
        invoice_id=_require_str(d, "invoice_id"),
        serial=_require_str(d, "serial"),
        template_code=_require_str(d, "template_code"),
        invoice_number=_require_int(d, "invoice_number"),
        kind=InvoiceKind(_require_str(d, "kind")),
        seller_tax_code=TaxCode(digits=_require_str(d, "seller_tax_code")),
        seller_name=_require_str(d, "seller_name"),
        buyer_tax_code=TaxCode(digits=buyer_mst_raw) if buyer_mst_raw else None,
        buyer_name=_optional_str(d, "buyer_name"),
        issued_at=datetime.fromisoformat(_require_str(d, "issued_at")),
        items=items,
        subtotal_vnd=_require_int(d, "subtotal_vnd"),
        vat_total_vnd=_require_int(d, "vat_total_vnd"),
        grand_total_vnd=_require_int(d, "grand_total_vnd"),
        currency=_optional_str(d, "currency") or "VND",
    )


def finding_to_dict(f: Finding) -> dict[str, object]:
    return {
        "invoice_id": f.invoice_id,
        "severity": f.severity.value,
        "code": f.code,
        "detail": f.detail,
    }


def finding_from_dict(d: dict[str, object]) -> Finding:
    return Finding(
        invoice_id=_require_str(d, "invoice_id"),
        severity=Severity(_require_str(d, "severity")),
        code=_require_str(d, "code"),
        detail=_require_str(d, "detail"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_invoices(invoices: Iterable[Invoice]) -> str:
    return _dump(invoice_to_dict(i) for i in invoices)


def dump_findings(findings: Iterable[Finding]) -> str:
    return _dump(finding_to_dict(f) for f in findings)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_invoices(text: str) -> Iterator[Invoice]:
    for d in _iter_lines(text):
        yield invoice_from_dict(d)


def load_findings(text: str) -> Iterator[Finding]:
    for d in _iter_lines(text):
        yield finding_from_dict(d)


__all__ = [
    "dump_findings",
    "dump_invoices",
    "finding_from_dict",
    "finding_to_dict",
    "invoice_from_dict",
    "invoice_to_dict",
    "load_findings",
    "load_invoices",
]
