"""lsm-merge-iterator — k-way merge of sorted runs."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Record": ("lsmmerge.schema", "Record"),
        "merge_runs": ("lsmmerge.merge", "merge_runs"),
        "generate_runs": ("lsmmerge.simulator", "generate_runs"),
        "dump_records": ("lsmmerge.io_jsonl", "dump_records"),
        "load_records": ("lsmmerge.io_jsonl", "load_records"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Record",
    "__version__",
    "dump_records",
    "generate_runs",
    "load_records",
    "merge_runs",
]
