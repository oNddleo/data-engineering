"""deadletter-queue-toolkit — DLQ + retry + classifier."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "DeadLetter": ("dlq.schema", "DeadLetter"),
    "FailureKind": ("dlq.schema", "FailureKind"),
    "classify": ("dlq.schema", "classify"),
    "JitterMode": ("dlq.retry", "JitterMode"),
    "RetryPolicy": ("dlq.retry", "RetryPolicy"),
    "next_backoff_ms": ("dlq.retry", "next_backoff_ms"),
    "should_retry": ("dlq.retry", "should_retry"),
    "DeadLetterQueue": ("dlq.queue", "DeadLetterQueue"),
    "ReplayResult": ("dlq.queue", "ReplayResult"),
    "generate": ("dlq.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from dlq.queue import DeadLetterQueue, ReplayResult
    from dlq.retry import JitterMode, RetryPolicy, next_backoff_ms, should_retry
    from dlq.schema import DeadLetter, FailureKind, classify
    from dlq.simulator import generate

__all__ = [
    "DeadLetter",
    "DeadLetterQueue",
    "FailureKind",
    "JitterMode",
    "ReplayResult",
    "RetryPolicy",
    "__version__",
    "classify",
    "generate",
    "next_backoff_ms",
    "should_retry",
]
