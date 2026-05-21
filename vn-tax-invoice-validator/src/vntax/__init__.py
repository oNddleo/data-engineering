"""vn-tax-invoice-validator — VN e-invoice validation per Decree 123 / TT 78."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Finding": ("vntax.validator", "Finding"),
        "InMemoryRegistry": ("vntax.registry", "InMemoryRegistry"),
        "Invoice": ("vntax.schema", "Invoice"),
        "InvoiceItem": ("vntax.schema", "InvoiceItem"),
        "InvoiceKind": ("vntax.schema", "InvoiceKind"),
        "Severity": ("vntax.validator", "Severity"),
        "TaxCode": ("vntax.schema", "TaxCode"),
        "TaxEntity": ("vntax.registry", "TaxEntity"),
        "TaxRegistry": ("vntax.registry", "TaxRegistry"),
        "VATRate": ("vntax.schema", "VATRate"),
        "VN_TZ": ("vntax.schema", "VN_TZ"),
        "check_export_invoice": ("vntax.validator", "check_export_invoice"),
        "check_line_math": ("vntax.validator", "check_line_math"),
        "check_required_fields": ("vntax.validator", "check_required_fields"),
        "check_tax_code_format": ("vntax.validator", "check_tax_code_format"),
        "check_template_consistency": ("vntax.validator", "check_template_consistency"),
        "check_totals": ("vntax.validator", "check_totals"),
        "compute_check_digit": ("vntax.taxcode", "compute_check_digit"),
        "dump_findings": ("vntax.io_jsonl", "dump_findings"),
        "dump_invoices": ("vntax.io_jsonl", "dump_invoices"),
        "finding_from_dict": ("vntax.io_jsonl", "finding_from_dict"),
        "finding_to_dict": ("vntax.io_jsonl", "finding_to_dict"),
        "generate": ("vntax.simulator", "generate"),
        "has_errors": ("vntax.validator", "has_errors"),
        "invoice_from_dict": ("vntax.io_jsonl", "invoice_from_dict"),
        "invoice_to_dict": ("vntax.io_jsonl", "invoice_to_dict"),
        "is_valid": ("vntax.taxcode", "is_valid"),
        "load_findings": ("vntax.io_jsonl", "load_findings"),
        "load_invoices": ("vntax.io_jsonl", "load_invoices"),
        "normalise": ("vntax.taxcode", "normalise"),
        "validate": ("vntax.validator", "validate"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "VN_TZ",
    "Finding",
    "InMemoryRegistry",
    "Invoice",
    "InvoiceItem",
    "InvoiceKind",
    "Severity",
    "TaxCode",
    "TaxEntity",
    "TaxRegistry",
    "VATRate",
    "__version__",
    "check_export_invoice",
    "check_line_math",
    "check_required_fields",
    "check_tax_code_format",
    "check_template_consistency",
    "check_totals",
    "compute_check_digit",
    "dump_findings",
    "dump_invoices",
    "finding_from_dict",
    "finding_to_dict",
    "generate",
    "has_errors",
    "invoice_from_dict",
    "invoice_to_dict",
    "is_valid",
    "load_findings",
    "load_invoices",
    "normalise",
    "validate",
]
