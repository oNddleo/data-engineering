"""incremental-file-watcher — event-driven S3/MinIO file watcher."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "EventKind": ("ifw.events", "EventKind"),
        "FileEvent": ("ifw.events", "FileEvent"),
        "Manifest": ("ifw.manifest", "Manifest"),
        "ManifestEntry": ("ifw.manifest", "ManifestEntry"),
        "Deduplicator": ("ifw.dedupe", "Deduplicator"),
        "LateArrivalDetector": ("ifw.late", "LateArrivalDetector"),
        "Backend": ("ifw.backends.base", "Backend"),
        "InMemoryBackend": ("ifw.backends.inmemory", "InMemoryBackend"),
        "PollingBackend": ("ifw.backends.polling", "PollingBackend"),
        "S3SqsBackend": ("ifw.backends.s3_sqs", "S3SqsBackend"),
        "parse_s3_event": ("ifw.backends.s3_sqs", "parse_s3_event"),
        "Runner": ("ifw.runner", "Runner"),
        "RunReport": ("ifw.runner", "RunReport"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Backend",
    "Deduplicator",
    "EventKind",
    "FileEvent",
    "InMemoryBackend",
    "LateArrivalDetector",
    "Manifest",
    "ManifestEntry",
    "PollingBackend",
    "RunReport",
    "Runner",
    "S3SqsBackend",
    "__version__",
    "parse_s3_event",
]
