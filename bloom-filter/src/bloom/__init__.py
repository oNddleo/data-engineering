"""bloom-filter — classic, counting, scalable Bloom filters in pure stdlib."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from bloom.counting import (
        add_counting,
        build_counting,
        contains_counting,
        remove_counting,
    )
    from bloom.filter import (
        add,
        build,
        contains,
        freeze,
        intersect_estimate,
        thaw,
        union,
    )
    from bloom.hash import hash64, positions
    from bloom.io_jsonl import (
        buildable_from_dict,
        buildable_to_dict,
        counting_from_dict,
        counting_to_dict,
        dump_filters,
        filter_from_dict,
        filter_to_dict,
        load_filters,
        scalable_from_dict,
        scalable_to_dict,
    )
    from bloom.scalable import (
        add_scalable,
        build_scalable,
        contains_scalable,
        cumulative_fpr_bound,
    )
    from bloom.schema import (
        BloomFilter,
        BuildableBloom,
        CountingBloom,
        ScalableBloom,
    )
    from bloom.simulator import mixed_stream, uniform_stream, zipf_stream
    from bloom.sizing import (
        bits_per_item,
        estimate_fpr,
        estimate_fpr_from_fill,
        optimal_n_hashes,
        optimal_size_bits,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "BloomFilter": ("bloom.schema", "BloomFilter"),
    "BuildableBloom": ("bloom.schema", "BuildableBloom"),
    "CountingBloom": ("bloom.schema", "CountingBloom"),
    "ScalableBloom": ("bloom.schema", "ScalableBloom"),
    "add": ("bloom.filter", "add"),
    "add_counting": ("bloom.counting", "add_counting"),
    "add_scalable": ("bloom.scalable", "add_scalable"),
    "bits_per_item": ("bloom.sizing", "bits_per_item"),
    "build": ("bloom.filter", "build"),
    "build_counting": ("bloom.counting", "build_counting"),
    "build_scalable": ("bloom.scalable", "build_scalable"),
    "buildable_from_dict": ("bloom.io_jsonl", "buildable_from_dict"),
    "buildable_to_dict": ("bloom.io_jsonl", "buildable_to_dict"),
    "contains": ("bloom.filter", "contains"),
    "contains_counting": ("bloom.counting", "contains_counting"),
    "contains_scalable": ("bloom.scalable", "contains_scalable"),
    "counting_from_dict": ("bloom.io_jsonl", "counting_from_dict"),
    "counting_to_dict": ("bloom.io_jsonl", "counting_to_dict"),
    "cumulative_fpr_bound": ("bloom.scalable", "cumulative_fpr_bound"),
    "dump_filters": ("bloom.io_jsonl", "dump_filters"),
    "estimate_fpr": ("bloom.sizing", "estimate_fpr"),
    "estimate_fpr_from_fill": ("bloom.sizing", "estimate_fpr_from_fill"),
    "filter_from_dict": ("bloom.io_jsonl", "filter_from_dict"),
    "filter_to_dict": ("bloom.io_jsonl", "filter_to_dict"),
    "freeze": ("bloom.filter", "freeze"),
    "hash64": ("bloom.hash", "hash64"),
    "intersect_estimate": ("bloom.filter", "intersect_estimate"),
    "load_filters": ("bloom.io_jsonl", "load_filters"),
    "mixed_stream": ("bloom.simulator", "mixed_stream"),
    "optimal_n_hashes": ("bloom.sizing", "optimal_n_hashes"),
    "optimal_size_bits": ("bloom.sizing", "optimal_size_bits"),
    "positions": ("bloom.hash", "positions"),
    "remove_counting": ("bloom.counting", "remove_counting"),
    "scalable_from_dict": ("bloom.io_jsonl", "scalable_from_dict"),
    "scalable_to_dict": ("bloom.io_jsonl", "scalable_to_dict"),
    "thaw": ("bloom.filter", "thaw"),
    "uniform_stream": ("bloom.simulator", "uniform_stream"),
    "union": ("bloom.filter", "union"),
    "zipf_stream": ("bloom.simulator", "zipf_stream"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BloomFilter",
    "BuildableBloom",
    "CountingBloom",
    "ScalableBloom",
    "__version__",
    "add",
    "add_counting",
    "add_scalable",
    "bits_per_item",
    "build",
    "build_counting",
    "build_scalable",
    "buildable_from_dict",
    "buildable_to_dict",
    "contains",
    "contains_counting",
    "contains_scalable",
    "counting_from_dict",
    "counting_to_dict",
    "cumulative_fpr_bound",
    "dump_filters",
    "estimate_fpr",
    "estimate_fpr_from_fill",
    "filter_from_dict",
    "filter_to_dict",
    "freeze",
    "hash64",
    "intersect_estimate",
    "load_filters",
    "mixed_stream",
    "optimal_n_hashes",
    "optimal_size_bits",
    "positions",
    "remove_counting",
    "scalable_from_dict",
    "scalable_to_dict",
    "thaw",
    "uniform_stream",
    "union",
    "zipf_stream",
]
