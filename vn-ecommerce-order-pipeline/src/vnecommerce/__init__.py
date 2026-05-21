"""Vietnam e-commerce order normalisation pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "Platform": ("vnecommerce.schema", "Platform"),
        "OrderStatus": ("vnecommerce.schema", "OrderStatus"),
        "PaymentMethod": ("vnecommerce.schema", "PaymentMethod"),
        "ShippingMethod": ("vnecommerce.schema", "ShippingMethod"),
        "RawOrder": ("vnecommerce.schema", "RawOrder"),
        "NormalisedOrder": ("vnecommerce.normaliser", "NormalisedOrder"),
        "normalise": ("vnecommerce.normaliser", "normalise"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = [
    "Platform",
    "OrderStatus",
    "PaymentMethod",
    "ShippingMethod",
    "RawOrder",
    "NormalisedOrder",
    "normalise",
]
