"""Intelligent Compaction Engine."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "DataFile": "compact.schema",
        "Partition": "compact.schema",
        "TableMeta": "compact.schema",
        "CompactionAction": "compact.schema",
        "CompactionPlan": "compact.schema",
        "QueryPattern": "compact.schema",
        "CompactionEngine": "compact.engine",
        "plan": "compact.engine",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'compact' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = [
    "CompactionAction",
    "CompactionEngine",
    "CompactionPlan",
    "DataFile",
    "Partition",
    "QueryPattern",
    "TableMeta",
    "plan",
]
