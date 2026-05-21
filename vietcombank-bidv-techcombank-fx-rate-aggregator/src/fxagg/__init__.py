"""vietcombank-bidv-techcombank-fx-rate-aggregator — FX rate aggregator + spread analyzer."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Alert": ("fxagg.spread", "Alert"),
        "AlertKind": ("fxagg.spread", "AlertKind"),
        "Bank": ("fxagg.schema", "Bank"),
        "Currency": ("fxagg.schema", "Currency"),
        "CurrencyAnalysis": ("fxagg.spread", "CurrencyAnalysis"),
        "ParseError": ("fxagg.parsers", "ParseError"),
        "Quote": ("fxagg.schema", "Quote"),
        "Severity": ("fxagg.spread", "Severity"),
        "Snapshot": ("fxagg.schema", "Snapshot"),
        "TimeSeriesStore": ("fxagg.storage", "TimeSeriesStore"),
        "VN_TZ": ("fxagg.schema", "VN_TZ"),
        "analyze": ("fxagg.spread", "analyze"),
        "dump_quotes": ("fxagg.storage", "dump_quotes"),
        "generate": ("fxagg.simulator", "generate"),
        "load_quotes": ("fxagg.storage", "load_quotes"),
        "load_store": ("fxagg.storage", "load_store"),
        "parse_bidv_html": ("fxagg.parsers", "parse_bidv_html"),
        "parse_generic_csv": ("fxagg.parsers", "parse_generic_csv"),
        "parse_techcombank_json": ("fxagg.parsers", "parse_techcombank_json"),
        "parse_vietcombank_xml": ("fxagg.parsers", "parse_vietcombank_xml"),
        "quote_from_dict": ("fxagg.storage", "quote_from_dict"),
        "quote_to_dict": ("fxagg.storage", "quote_to_dict"),
        "save_store": ("fxagg.storage", "save_store"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "VN_TZ",
    "Alert",
    "AlertKind",
    "Bank",
    "Currency",
    "CurrencyAnalysis",
    "ParseError",
    "Quote",
    "Severity",
    "Snapshot",
    "TimeSeriesStore",
    "__version__",
    "analyze",
    "dump_quotes",
    "generate",
    "load_quotes",
    "load_store",
    "parse_bidv_html",
    "parse_generic_csv",
    "parse_techcombank_json",
    "parse_vietcombank_xml",
    "quote_from_dict",
    "quote_to_dict",
    "save_store",
]
