"""Vietnam rice supply chain pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "PaddyGrade": ("vnrice.schema", "PaddyGrade"),
        "RiceVariety": ("vnrice.schema", "RiceVariety"),
        "PaddyLot": ("vnrice.schema", "PaddyLot"),
        "MilledLot": ("vnrice.milling", "MilledLot"),
        "mill": ("vnrice.milling", "mill"),
        "ExportQuote": ("vnrice.pricing", "ExportQuote"),
        "quote_export": ("vnrice.pricing", "quote_export"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = [
    "PaddyGrade",
    "RiceVariety",
    "PaddyLot",
    "MilledLot",
    "mill",
    "ExportQuote",
    "quote_export",
]
