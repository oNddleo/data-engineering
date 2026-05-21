"""Timely Dataflow Engine (Naiad-style)."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "Timestamp": "timely.timestamp.ts",
        "Antichain": "timely.timestamp.antichain",
        "ProgressTracker": "timely.progress.tracker",
        "GraphBuilder": "timely.graph.builder",
        "Runtime": "timely.graph.runtime",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'timely' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = ["Antichain", "GraphBuilder", "ProgressTracker", "Runtime", "Timestamp"]
