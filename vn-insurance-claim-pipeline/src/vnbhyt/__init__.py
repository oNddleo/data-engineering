"""vn-insurance-claim-pipeline — BHYT claim normaliser + payout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "CardClass": ("vnbhyt.schema", "CardClass"),
    "CareType": ("vnbhyt.schema", "CareType"),
    "Claim": ("vnbhyt.schema", "Claim"),
    "HospitalTier": ("vnbhyt.schema", "HospitalTier"),
    "Payout": ("vnbhyt.payout", "Payout"),
    "compute": ("vnbhyt.payout", "compute"),
    "generate": ("vnbhyt.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from vnbhyt.payout import Payout, compute
    from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier
    from vnbhyt.simulator import generate

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
