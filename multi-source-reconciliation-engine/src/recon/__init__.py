"""Multi-Source Reconciliation Engine."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "Transaction": "recon.schema",
        "DiscrepancyType": "recon.schema",
        "MatchResult": "recon.schema",
        "ReconReport": "recon.schema",
        "ReconciliationEngine": "recon.engine",
        "reconcile": "recon.engine",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'recon' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = [
    "DiscrepancyType",
    "MatchResult",
    "ReconReport",
    "ReconciliationEngine",
    "Transaction",
    "reconcile",
]
