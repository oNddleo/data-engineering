"""hyperloglog-cardinality — HyperLogLog++ sketches for distinct counting."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "DEFAULT_PRECISION": ("hllpp.schema", "DEFAULT_PRECISION"),
        "HLLSketch": ("hllpp.schema", "HLLSketch"),
        "MAX_PRECISION": ("hllpp.schema", "MAX_PRECISION"),
        "MIN_PRECISION": ("hllpp.schema", "MIN_PRECISION"),
        "SketchStats": ("hllpp.schema", "SketchStats"),
        "StreamPattern": ("hllpp.simulator", "StreamPattern"),
        "add": ("hllpp.sketch", "add"),
        "dump_sketches": ("hllpp.io_jsonl", "dump_sketches"),
        "estimate": ("hllpp.sketch", "estimate"),
        "generate": ("hllpp.simulator", "generate"),
        "hash64": ("hllpp.hash", "hash64"),
        "leading_zeros_64": ("hllpp.hash", "leading_zeros_64"),
        "load_sketches": ("hllpp.io_jsonl", "load_sketches"),
        "merge": ("hllpp.sketch", "merge"),
        "new_sketch": ("hllpp.sketch", "new_sketch"),
        "sketch_from_dict": ("hllpp.io_jsonl", "sketch_from_dict"),
        "sketch_to_dict": ("hllpp.io_jsonl", "sketch_to_dict"),
        "stats": ("hllpp.sketch", "stats"),
        "stats_from_dict": ("hllpp.io_jsonl", "stats_from_dict"),
        "stats_to_dict": ("hllpp.io_jsonl", "stats_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "DEFAULT_PRECISION",
    "HLLSketch",
    "MAX_PRECISION",
    "MIN_PRECISION",
    "SketchStats",
    "StreamPattern",
    "__version__",
    "add",
    "dump_sketches",
    "estimate",
    "generate",
    "hash64",
    "leading_zeros_64",
    "load_sketches",
    "merge",
    "new_sketch",
    "sketch_from_dict",
    "sketch_to_dict",
    "stats",
    "stats_from_dict",
    "stats_to_dict",
]
