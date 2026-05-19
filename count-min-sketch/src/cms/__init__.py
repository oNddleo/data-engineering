"""count-min-sketch — frequency estimation sketches at streaming scale."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from cms.hash import hash64, index_for
    from cms.heavy import (
        HeavyHittersBuilder,
        exact_heavy_hitters,
        top_k_two_pass,
    )
    from cms.io_jsonl import (
        dump_heavy_hitters,
        dump_sketches,
        heavy_hitter_from_dict,
        heavy_hitter_to_dict,
        load_heavy_hitters,
        load_sketches,
        sketch_from_dict,
        sketch_to_dict,
        stats_from_dict,
        stats_to_dict,
    )
    from cms.schema import (
        MAX_COUNT,
        CountMinSketch,
        HeavyHitter,
        SketchConfig,
        SketchStats,
    )
    from cms.simulator import StreamPattern, generate
    from cms.sketch import estimate, merge, new_sketch, stats, update


_LAZY: dict[str, tuple[str, str]] = {
    "CountMinSketch": ("cms.schema", "CountMinSketch"),
    "HeavyHitter": ("cms.schema", "HeavyHitter"),
    "HeavyHittersBuilder": ("cms.heavy", "HeavyHittersBuilder"),
    "MAX_COUNT": ("cms.schema", "MAX_COUNT"),
    "SketchConfig": ("cms.schema", "SketchConfig"),
    "SketchStats": ("cms.schema", "SketchStats"),
    "StreamPattern": ("cms.simulator", "StreamPattern"),
    "dump_heavy_hitters": ("cms.io_jsonl", "dump_heavy_hitters"),
    "dump_sketches": ("cms.io_jsonl", "dump_sketches"),
    "estimate": ("cms.sketch", "estimate"),
    "exact_heavy_hitters": ("cms.heavy", "exact_heavy_hitters"),
    "generate": ("cms.simulator", "generate"),
    "hash64": ("cms.hash", "hash64"),
    "heavy_hitter_from_dict": ("cms.io_jsonl", "heavy_hitter_from_dict"),
    "heavy_hitter_to_dict": ("cms.io_jsonl", "heavy_hitter_to_dict"),
    "index_for": ("cms.hash", "index_for"),
    "load_heavy_hitters": ("cms.io_jsonl", "load_heavy_hitters"),
    "load_sketches": ("cms.io_jsonl", "load_sketches"),
    "merge": ("cms.sketch", "merge"),
    "new_sketch": ("cms.sketch", "new_sketch"),
    "sketch_from_dict": ("cms.io_jsonl", "sketch_from_dict"),
    "sketch_to_dict": ("cms.io_jsonl", "sketch_to_dict"),
    "stats": ("cms.sketch", "stats"),
    "stats_from_dict": ("cms.io_jsonl", "stats_from_dict"),
    "stats_to_dict": ("cms.io_jsonl", "stats_to_dict"),
    "top_k_two_pass": ("cms.heavy", "top_k_two_pass"),
    "update": ("cms.sketch", "update"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CountMinSketch",
    "HeavyHitter",
    "HeavyHittersBuilder",
    "MAX_COUNT",
    "SketchConfig",
    "SketchStats",
    "StreamPattern",
    "__version__",
    "dump_heavy_hitters",
    "dump_sketches",
    "estimate",
    "exact_heavy_hitters",
    "generate",
    "hash64",
    "heavy_hitter_from_dict",
    "heavy_hitter_to_dict",
    "index_for",
    "load_heavy_hitters",
    "load_sketches",
    "merge",
    "new_sketch",
    "sketch_from_dict",
    "sketch_to_dict",
    "stats",
    "stats_from_dict",
    "stats_to_dict",
    "top_k_two_pass",
    "update",
]
