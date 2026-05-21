"""idempotency-key-store — at-most-once execution via idempotency keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "EntryStatus": ("idempotency.schema", "EntryStatus"),
    "IdempotencyEntry": ("idempotency.schema", "IdempotencyEntry"),
    "fingerprint": ("idempotency.schema", "fingerprint"),
    "IdempotencyStore": ("idempotency.store", "IdempotencyStore"),
    "Outcome": ("idempotency.store", "Outcome"),
    "ReserveResult": ("idempotency.store", "ReserveResult"),
    "SyntheticRequest": ("idempotency.simulator", "SyntheticRequest"),
    "generate": ("idempotency.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from idempotency.schema import EntryStatus, IdempotencyEntry, fingerprint
    from idempotency.simulator import SyntheticRequest, generate
    from idempotency.store import IdempotencyStore, Outcome, ReserveResult

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
