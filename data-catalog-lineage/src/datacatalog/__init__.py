"""Data catalog with PII detection and column-level lineage tracking."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "Column": "datacatalog.schema",
        "Table": "datacatalog.schema",
        "DataSource": "datacatalog.schema",
        "LineageEdge": "datacatalog.schema",
        "PIICategory": "datacatalog.schema",
        "PIIDetector": "datacatalog.pii",
        "LineageGraph": "datacatalog.lineage",
        "DataCatalog": "datacatalog.catalog",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'datacatalog' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)
