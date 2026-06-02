"""minio-iceberg-lakehouse — from-scratch Iceberg-style table format."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Field": ("lake.schema", "Field"),
        "FieldType": ("lake.schema", "FieldType"),
        "Schema": ("lake.schema", "Schema"),
        "SchemaEvolutionError": ("lake.schema", "SchemaEvolutionError"),
        "DataFile": ("lake.datafile", "DataFile"),
        "Manifest": ("lake.manifest", "Manifest"),
        "Snapshot": ("lake.snapshot", "Snapshot"),
        "SnapshotOp": ("lake.snapshot", "SnapshotOp"),
        "TableMetadata": ("lake.metadata", "TableMetadata"),
        "Storage": ("lake.storage.base", "Storage"),
        "InMemoryStorage": ("lake.storage.inmemory", "InMemoryStorage"),
        "LocalFSStorage": ("lake.storage.local_fs", "LocalFSStorage"),
        "Table": ("lake.table", "Table"),
        "TableError": ("lake.table", "TableError"),
        "Catalog": ("lake.catalog", "Catalog"),
        "CatalogError": ("lake.catalog", "CatalogError"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Catalog",
    "CatalogError",
    "DataFile",
    "Field",
    "FieldType",
    "InMemoryStorage",
    "LocalFSStorage",
    "Manifest",
    "Schema",
    "SchemaEvolutionError",
    "Snapshot",
    "SnapshotOp",
    "Storage",
    "Table",
    "TableError",
    "TableMetadata",
    "__version__",
]
