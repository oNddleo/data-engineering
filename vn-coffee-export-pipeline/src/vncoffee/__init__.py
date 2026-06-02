"""Vietnam coffee export pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "CoffeeGrade": ("vncoffee.schema", "CoffeeGrade"),
        "ContractType": ("vncoffee.schema", "ContractType"),
        "ExportLot": ("vncoffee.schema", "ExportLot"),
        "PricedLot": ("vncoffee.pricing", "PricedLot"),
        "price_lot": ("vncoffee.pricing", "price_lot"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["CoffeeGrade", "ContractType", "ExportLot", "PricedLot", "price_lot"]
