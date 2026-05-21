"""lsm-merge-iterator — k-way merge of sorted runs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "Record": ("lsmmerge.schema", "Record"),
    "merge_runs": ("lsmmerge.merge", "merge_runs"),
    "generate_runs": ("lsmmerge.simulator", "generate_runs"),
    "dump_records": ("lsmmerge.io_jsonl", "dump_records"),
    "load_records": ("lsmmerge.io_jsonl", "load_records"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from lsmmerge.io_jsonl import dump_records, load_records
    from lsmmerge.merge import merge_runs
    from lsmmerge.schema import Record
    from lsmmerge.simulator import generate_runs

__all__ = [
    "Record",
    "__version__",
    "dump_records",
    "generate_runs",
    "load_records",
    "merge_runs",
]
