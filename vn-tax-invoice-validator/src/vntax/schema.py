"""Vietnamese e-invoice schema per Nghị định 123/2020/NĐ-CP + Thông tư 78/2021/TT-BTC.

A Vietnamese electronic invoice (hóa đơn điện tử) is the legal
equivalent of a printed VAT invoice. Every commercial transaction
above 200,000 VND must have one. The format is JSON / XML over the
General Department of Taxation (GDT, Tổng cục Thuế) submission API.

This module models the **shape** — required fields per Decree 123 —
plus the four legal VAT rates and the invoice template/symbol
metadata that lets ``vntax.validator`` cross-check the math.

| VAT rate | When used                                                         |
| -------- | ----------------------------------------------------------------- |
| 0%       | Exports, international transport, services to foreign zones       |
| 5%       | Essential goods (clean water, fertilizer, medical equipment, …)   |
| 8%       | Reduced rate per Nghị quyết 43/2022/QH15 — Covid-era stimulus, extended through 2024-2026 for most goods otherwise at 10% |
| 10%      | Standard rate — everything else                                   |
| NA       | VAT-exempt goods (rice, salt, healthcare) — not the same as 0%    |

The 8% rate is the most error-prone in production. It applies to
most goods that *would otherwise* be at 10%, but with carve-outs
(luxury goods, finance, telecom, IT services stay at 10%). Most
real-world invoice rejections we model trace to a wrong 8% / 10%
classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class VATRate(int, Enum):
    """Legal Vietnamese VAT rates in basis points (1% = 100 bps)."""

    EXEMPT = -1  # VAT-exempt (different from 0%); skipped in math
    ZERO = 0  # 0% — export, intl. transport
    FIVE = 500  # 5% — essential goods
    EIGHT = 800  # 8% — Nghị quyết 43 / extension stimulus rate
    TEN = 1000  # 10% — standard rate


class InvoiceKind(str, Enum):
    """Per Thông tư 78 Article 9 — the kind drives template + symbol rules."""

    VAT_INVOICE = "VAT_INVOICE"  # Hóa đơn GTGT
    SALES_INVOICE = "SALES_INVOICE"  # Hóa đơn bán hàng (non-VAT registered)
    EXPORT_INVOICE = "EXPORT_INVOICE"  # Hóa đơn xuất khẩu


@dataclass(frozen=True, slots=True)
class TaxCode:
    """A Vietnamese tax ID (Mã số thuế, MST).

    There are two legal forms:

    * **10-digit** — the legal entity's primary MST.
    * **13-digit** — a 10-digit primary + 3-digit branch suffix
      (used for branches / dependent units).

    Both share the same 10-digit checksum on the primary portion.
    The 13-digit branch suffix is **not** checksum-validated by GDT.
    """

    digits: str

    def __post_init__(self) -> None:
        if not self.digits.isascii() or not self.digits.isdigit():
            raise ValueError(f"tax code must be all digits, got {self.digits!r}")
        if len(self.digits) not in (10, 13):
            raise ValueError(f"tax code must be 10 or 13 digits, got {len(self.digits)}")

    @property
    def primary(self) -> str:
        """The 10-digit primary portion."""
        return self.digits[:10]

    @property
    def branch_suffix(self) -> str | None:
        """The 3-digit branch suffix for 13-digit codes; ``None`` otherwise."""
        return self.digits[10:] if len(self.digits) == 13 else None


@dataclass(frozen=True, slots=True)
class InvoiceItem:
    """One line on an invoice. Money in integer VND."""

    line_no: int  # 1-indexed
    description: str
    quantity: int  # whole units (decimal qty not supported; sub-unit prices stored elsewhere)
    unit_price_vnd: int  # before VAT
    vat_rate: VATRate
    line_total_vnd: int  # quantity × unit_price_vnd (validator will check)
    vat_amount_vnd: int  # line_total × rate_bps / 10_000 (validator will check)

    def __post_init__(self) -> None:
        if self.line_no < 1:
            raise ValueError(f"line_no must be >= 1, got {self.line_no}")
        if not self.description:
            raise ValueError("description must be non-empty")
        if self.quantity < 1:
            raise ValueError(f"quantity must be >= 1, got {self.quantity}")
        if self.unit_price_vnd < 0:
            raise ValueError(f"unit_price_vnd must be >= 0, got {self.unit_price_vnd}")
        if self.line_total_vnd < 0:
            raise ValueError(f"line_total_vnd must be >= 0, got {self.line_total_vnd}")
        if self.vat_amount_vnd < 0:
            raise ValueError(f"vat_amount_vnd must be >= 0, got {self.vat_amount_vnd}")


@dataclass(frozen=True, slots=True)
class Invoice:
    """One e-invoice header + lines.

    The ``serial`` / ``invoice_number`` pair is the legal identity
    GDT uses to deduplicate submissions. ``template_code`` encodes
    the invoice type (1 = VAT, 2 = sales, 6 = export) per Thông tư 78.
    """

    invoice_id: str  # internal UUID
    serial: str  # ký hiệu hóa đơn (e.g. "K22TAA")
    template_code: str  # mẫu số (e.g. "1/001")
    invoice_number: int  # số hóa đơn (sequential within serial)
    kind: InvoiceKind
    seller_tax_code: TaxCode
    seller_name: str
    buyer_tax_code: TaxCode | None  # nullable for B2C retail invoices
    buyer_name: str | None
    issued_at: datetime
    items: tuple[InvoiceItem, ...]
    subtotal_vnd: int  # sum of line_total
    vat_total_vnd: int  # sum of vat_amount
    grand_total_vnd: int  # subtotal + vat_total
    currency: str = "VND"

    def __post_init__(self) -> None:
        if not self.invoice_id:
            raise ValueError("invoice_id must be non-empty")
        if not self.serial:
            raise ValueError("serial must be non-empty")
        if not self.template_code:
            raise ValueError("template_code must be non-empty")
        if self.invoice_number < 1:
            raise ValueError(f"invoice_number must be >= 1, got {self.invoice_number}")
        if not self.seller_name:
            raise ValueError("seller_name must be non-empty")
        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")
        if not self.items:
            raise ValueError("invoice must have at least one item")
        if self.subtotal_vnd < 0 or self.vat_total_vnd < 0 or self.grand_total_vnd < 0:
            raise ValueError("totals must be >= 0")
        if self.currency != "VND":
            raise ValueError(f"currency must be VND, got {self.currency!r}")
        # Line numbers must be 1..N contiguous (GDT rejects gaps).
        expected = list(range(1, len(self.items) + 1))
        actual = [i.line_no for i in self.items]
        if actual != expected:
            raise ValueError(f"line_no must be 1..N contiguous, got {actual}")


__all__ = ["VN_TZ", "Invoice", "InvoiceItem", "InvoiceKind", "TaxCode", "VATRate"]
