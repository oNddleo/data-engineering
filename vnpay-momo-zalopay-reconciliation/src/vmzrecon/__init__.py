"""vnpay-momo-zalopay-reconciliation — 3-way wallet settlement recon."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Discrepancy": ("vmzrecon.discrepancy", "Discrepancy"),
        "DiscrepancyKind": ("vmzrecon.discrepancy", "DiscrepancyKind"),
        "MerchantOrder": ("vmzrecon.schema", "MerchantOrder"),
        "ParseError": ("vmzrecon.parsers", "ParseError"),
        "Status": ("vmzrecon.schema", "Status"),
        "Summary": ("vmzrecon.report", "Summary"),
        "VN_TZ": ("vmzrecon.schema", "VN_TZ"),
        "Wallet": ("vmzrecon.schema", "Wallet"),
        "WalletTxn": ("vmzrecon.schema", "WalletTxn"),
        "format_csv_report": ("vmzrecon.report", "format_csv_report"),
        "format_json_report": ("vmzrecon.report", "format_json_report"),
        "format_text_report": ("vmzrecon.report", "format_text_report"),
        "parse_merchant_csv": ("vmzrecon.parsers", "parse_merchant_csv"),
        "parse_momo_csv": ("vmzrecon.parsers", "parse_momo_csv"),
        "parse_vnpay_csv": ("vmzrecon.parsers", "parse_vnpay_csv"),
        "parse_zalopay_csv": ("vmzrecon.parsers", "parse_zalopay_csv"),
        "reconcile": ("vmzrecon.matcher", "reconcile"),
        "summarise": ("vmzrecon.report", "summarise"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VN_TZ",
    "Discrepancy",
    "DiscrepancyKind",
    "MerchantOrder",
    "ParseError",
    "Status",
    "Summary",
    "Wallet",
    "WalletTxn",
    "__version__",
    "format_csv_report",
    "format_json_report",
    "format_text_report",
    "parse_merchant_csv",
    "parse_momo_csv",
    "parse_vnpay_csv",
    "parse_zalopay_csv",
    "reconcile",
    "summarise",
]
