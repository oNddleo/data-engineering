"""Vietnam petroleum pricing pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "FuelType": ("vnpetro.schema", "FuelType"),
        "PriceInput": ("vnpetro.schema", "PriceInput"),
        "PriceBreakdown": ("vnpetro.pricing", "PriceBreakdown"),
        "calculate_retail_price": ("vnpetro.pricing", "calculate_retail_price"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["FuelType", "PriceInput", "PriceBreakdown", "calculate_retail_price"]
