"""Invoice validator — the rules ops cares about.

Every check is a pure function over an ``Invoice`` (and optionally a
``TaxRegistry`` for the seller / buyer lookup). The validator collects
all failures rather than short-circuiting on the first — operators
fixing a bad invoice want the full punch list, not a one-issue
play-by-play.

| Check                         | What it catches                                |
| ----------------------------- | ---------------------------------------------- |
| ``check_tax_code_format``     | MST length / non-digit / checksum failure      |
| ``check_line_math``           | ``line_total ≠ qty × unit_price``              |
| ``check_vat_math``            | ``vat_amount ≠ line_total × rate_bps / 10_000`` (rounded to nearest VND) |
| ``check_totals``              | header totals don't match sum of lines         |
| ``check_required_fields``     | Decree-123 mandatory fields missing per kind   |
| ``check_export_invoice``      | EXPORT_INVOICE has VAT 0% only                 |
| ``check_template_consistency``| ``template_code`` matches ``InvoiceKind``      |

The 8% VAT-rate carve-outs (luxury / finance / telecom stay at 10%
even when other goods drop to 8%) are not validated here — they
require product-classification metadata we don't have at the invoice
layer. That check belongs in a separate product-master service.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from vntax.schema import InvoiceKind, VATRate
from vntax.taxcode import is_valid as is_valid_tax_code

if TYPE_CHECKING:
    from vntax.schema import Invoice, InvoiceItem


class Severity(str, Enum):
    """Validation findings are graded so dashboards can split into
    "must-fix before submission" vs "ops should review"."""

    ERROR = "ERROR"  # GDT will reject the submission
    WARNING = "WARNING"  # GDT may accept but ops should review


@dataclass(frozen=True, slots=True)
class Finding:
    """One ops-actionable problem with one invoice."""

    invoice_id: str
    severity: Severity
    code: str  # short stable ID for dashboards
    detail: str  # human-readable explanation


# Template-code → expected InvoiceKind per Thông tư 78 Article 9. The
# template's first character is the kind selector; everything after the
# slash is the form variant.
_TEMPLATE_KIND_FIRST_CHAR: dict[str, InvoiceKind] = {
    "1": InvoiceKind.VAT_INVOICE,
    "2": InvoiceKind.SALES_INVOICE,
    "6": InvoiceKind.EXPORT_INVOICE,
}


def _round_vat(line_total_vnd: int, rate: VATRate) -> int:
    """GDT's rounding rule: ``line_total × rate_bps / 10_000`` rounded
    to the nearest VND using **banker's rounding** on half cases.

    Python 3's built-in ``round`` already implements banker's, but we
    bypass it for integer-VND inputs to avoid the float trip.
    """
    if rate is VATRate.EXEMPT:
        return 0
    rate_bps: int = rate.value
    # Integer multiplication, then divide-with-rounding.
    numer = line_total_vnd * rate_bps
    denom = 10_000
    quot, rem = divmod(numer, denom)
    quot_int: int = quot
    # Round half to even.
    if rem * 2 > denom or (rem * 2 == denom and quot_int % 2 == 1):
        quot_int += 1
    return quot_int


def check_tax_code_format(invoice: Invoice) -> list[Finding]:
    """Seller MST must validate; buyer MST optional but must validate if present."""
    out: list[Finding] = []
    if not is_valid_tax_code(invoice.seller_tax_code.digits):
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="TAX_CODE_SELLER_INVALID",
                detail=f"seller MST {invoice.seller_tax_code.digits!r} fails checksum",
            )
        )
    if invoice.buyer_tax_code is not None and not is_valid_tax_code(invoice.buyer_tax_code.digits):
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="TAX_CODE_BUYER_INVALID",
                detail=f"buyer MST {invoice.buyer_tax_code.digits!r} fails checksum",
            )
        )
    return out


def _check_one_line(invoice_id: str, item: InvoiceItem) -> list[Finding]:
    out: list[Finding] = []
    expected_line = item.quantity * item.unit_price_vnd
    if item.line_total_vnd != expected_line:
        out.append(
            Finding(
                invoice_id=invoice_id,
                severity=Severity.ERROR,
                code="LINE_TOTAL_MISMATCH",
                detail=(
                    f"line {item.line_no}: line_total={item.line_total_vnd:,} "
                    f"≠ qty × unit_price = {expected_line:,}"
                ),
            )
        )
    expected_vat = _round_vat(item.line_total_vnd, item.vat_rate)
    if item.vat_amount_vnd != expected_vat:
        out.append(
            Finding(
                invoice_id=invoice_id,
                severity=Severity.ERROR,
                code="VAT_AMOUNT_MISMATCH",
                detail=(
                    f"line {item.line_no}: vat_amount={item.vat_amount_vnd:,} "
                    f"≠ expected {expected_vat:,} at rate {item.vat_rate.name}"
                ),
            )
        )
    return out


def check_line_math(invoice: Invoice) -> list[Finding]:
    """Every line: line_total == qty × unit_price; vat_amount == line × rate."""
    out: list[Finding] = []
    for item in invoice.items:
        out.extend(_check_one_line(invoice.invoice_id, item))
    return out


def check_totals(invoice: Invoice) -> list[Finding]:
    """Header subtotal / vat_total / grand_total match the sum of the lines."""
    out: list[Finding] = []
    expected_subtotal = sum(i.line_total_vnd for i in invoice.items)
    expected_vat = sum(i.vat_amount_vnd for i in invoice.items)
    expected_grand = expected_subtotal + expected_vat
    if invoice.subtotal_vnd != expected_subtotal:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="HEADER_SUBTOTAL_MISMATCH",
                detail=f"header subtotal={invoice.subtotal_vnd:,} ≠ sum(lines) {expected_subtotal:,}",
            )
        )
    if invoice.vat_total_vnd != expected_vat:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="HEADER_VAT_MISMATCH",
                detail=f"header vat_total={invoice.vat_total_vnd:,} ≠ sum(lines) {expected_vat:,}",
            )
        )
    if invoice.grand_total_vnd != expected_grand:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="HEADER_GRAND_MISMATCH",
                detail=(
                    f"header grand_total={invoice.grand_total_vnd:,} "
                    f"≠ subtotal + vat = {expected_grand:,}"
                ),
            )
        )
    return out


def check_required_fields(invoice: Invoice) -> list[Finding]:
    """Decree-123 fields that vary by ``InvoiceKind``."""
    out: list[Finding] = []
    # B2B VAT invoices must have a buyer tax code.
    if invoice.kind is InvoiceKind.VAT_INVOICE and invoice.buyer_tax_code is None:
        # WARNING (not ERROR) — retail VAT invoices to consumers are
        # legal without buyer MST; ops should confirm this is one.
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.WARNING,
                code="VAT_INVOICE_NO_BUYER_MST",
                detail="VAT invoice without buyer MST — confirm this is a retail (B2C) invoice",
            )
        )
    # Export invoices must name the buyer (foreign counterparty).
    if invoice.kind is InvoiceKind.EXPORT_INVOICE and not invoice.buyer_name:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="EXPORT_NO_BUYER_NAME",
                detail="EXPORT invoice must include buyer_name (foreign counterparty)",
            )
        )
    return out


def check_export_invoice(invoice: Invoice) -> list[Finding]:
    """EXPORT_INVOICE must be 0% VAT on every line."""
    if invoice.kind is not InvoiceKind.EXPORT_INVOICE:
        return []
    out: list[Finding] = []
    for item in invoice.items:
        if item.vat_rate is not VATRate.ZERO:
            out.append(
                Finding(
                    invoice_id=invoice.invoice_id,
                    severity=Severity.ERROR,
                    code="EXPORT_NON_ZERO_VAT",
                    detail=(
                        f"line {item.line_no}: EXPORT invoice has VAT rate {item.vat_rate.name}; "
                        f"exports must be 0%"
                    ),
                )
            )
    return out


def check_template_consistency(invoice: Invoice) -> list[Finding]:
    """``template_code`` first character must match ``invoice.kind``."""
    out: list[Finding] = []
    first = invoice.template_code[0]
    expected = _TEMPLATE_KIND_FIRST_CHAR.get(first)
    if expected is None:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="TEMPLATE_UNKNOWN",
                detail=f"template_code {invoice.template_code!r} starts with unknown selector {first!r}",
            )
        )
    elif expected is not invoice.kind:
        out.append(
            Finding(
                invoice_id=invoice.invoice_id,
                severity=Severity.ERROR,
                code="TEMPLATE_KIND_MISMATCH",
                detail=(
                    f"template_code {invoice.template_code!r} encodes {expected.value} "
                    f"but invoice.kind is {invoice.kind.value}"
                ),
            )
        )
    return out


_ALL_CHECKS = (
    check_tax_code_format,
    check_line_math,
    check_totals,
    check_required_fields,
    check_export_invoice,
    check_template_consistency,
)


def validate(invoice: Invoice) -> list[Finding]:
    """Run every check; return the union of findings.

    Output is sorted by (severity, code, invoice_id) for stable diffs.
    """
    findings: list[Finding] = []
    for check in _ALL_CHECKS:
        findings.extend(check(invoice))
    # ERROR before WARNING; then by code for stable ordering.
    findings.sort(key=lambda f: (0 if f.severity is Severity.ERROR else 1, f.code))
    return findings


def has_errors(findings: list[Finding]) -> bool:
    """``True`` if any finding is severity ERROR (would block GDT submission)."""
    return any(f.severity is Severity.ERROR for f in findings)


__all__ = [
    "Finding",
    "Severity",
    "check_export_invoice",
    "check_line_math",
    "check_required_fields",
    "check_tax_code_format",
    "check_template_consistency",
    "check_totals",
    "has_errors",
    "validate",
]
