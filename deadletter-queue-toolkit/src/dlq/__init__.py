"""deadletter-queue-toolkit — DLQ + retry + classifier."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
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

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
