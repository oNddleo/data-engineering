"""delta-vs-iceberg-vs-hudi — three mini table formats + workload comparison."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "DeltaTable": ("tfl.delta.table", "DeltaTable"),
        "Action": ("tfl.delta.action", "Action"),
        "ActionType": ("tfl.delta.action", "ActionType"),
        "FileEntry": ("tfl.delta.action", "FileEntry"),
        "IcebergTable": ("tfl.iceberg.table", "IcebergTable"),
        "HudiCoWTable": ("tfl.hudi.table", "HudiCoWTable"),
        "HudiMoRTable": ("tfl.hudi.table", "HudiMoRTable"),
        "CDCEvent": ("tfl.bench.workload", "CDCEvent"),
        "CDCOp": ("tfl.bench.workload", "CDCOp"),
        "Workload": ("tfl.bench.workload", "Workload"),
        "CompareReport": ("tfl.bench.compare", "CompareReport"),
        "run_workload": ("tfl.bench.compare", "run_workload"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Action",
    "ActionType",
    "CDCEvent",
    "CDCOp",
    "CompareReport",
    "DeltaTable",
    "FileEntry",
    "HudiCoWTable",
    "HudiMoRTable",
    "IcebergTable",
    "Workload",
    "__version__",
    "run_workload",
]
