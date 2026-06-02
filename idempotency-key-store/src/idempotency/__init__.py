"""idempotency-key-store — at-most-once execution via idempotency keys."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "EntryStatus": ("idempotency.schema", "EntryStatus"),
        "IdempotencyEntry": ("idempotency.schema", "IdempotencyEntry"),
        "fingerprint": ("idempotency.schema", "fingerprint"),
        "IdempotencyStore": ("idempotency.store", "IdempotencyStore"),
        "Outcome": ("idempotency.store", "Outcome"),
        "ReserveResult": ("idempotency.store", "ReserveResult"),
        "SyntheticRequest": ("idempotency.simulator", "SyntheticRequest"),
        "generate": ("idempotency.simulator", "generate"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "EntryStatus",
    "IdempotencyEntry",
    "IdempotencyStore",
    "Outcome",
    "ReserveResult",
    "SyntheticRequest",
    "__version__",
    "fingerprint",
    "generate",
]
