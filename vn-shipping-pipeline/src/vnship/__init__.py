"""Vietnam domestic shipping pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "Carrier": ("vnship.schema", "Carrier"),
        "DeliveryStatus": ("vnship.schema", "DeliveryStatus"),
        "ShipmentRequest": ("vnship.schema", "ShipmentRequest"),
        "ShipmentResult": ("vnship.schema", "ShipmentResult"),
        "calculate_fee": ("vnship.pricing", "calculate_fee"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = [
    "Carrier",
    "DeliveryStatus",
    "ShipmentRequest",
    "ShipmentResult",
    "calculate_fee",
]
