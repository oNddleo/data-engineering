"""vn-insurance-claim-pipeline — BHYT claim normaliser + payout."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "CardClass": ("vnbhyt.schema", "CardClass"),
        "CareType": ("vnbhyt.schema", "CareType"),
        "Claim": ("vnbhyt.schema", "Claim"),
        "HospitalTier": ("vnbhyt.schema", "HospitalTier"),
        "Payout": ("vnbhyt.payout", "Payout"),
        "compute": ("vnbhyt.payout", "compute"),
        "generate": ("vnbhyt.simulator", "generate"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CardClass",
    "CareType",
    "Claim",
    "HospitalTier",
    "Payout",
    "__version__",
    "compute",
    "generate",
]
