"""reservoir-sampling — Vitter R + Li L + Efraimidis–Spirakis A-Res."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from reservoir.algorithms import (
        add_l,
        add_r,
        add_weighted,
        build_l,
        build_r,
        build_weighted,
        freeze,
        sample_l,
        sample_r,
        sample_weighted,
        thaw,
    )
    from reservoir.io_jsonl import (
        dump_reservoirs,
        dump_weighted,
        load_reservoirs,
        load_weighted,
        reservoir_from_dict,
        reservoir_to_dict,
        weighted_from_dict,
        weighted_to_dict,
    )
    from reservoir.merge import merge_uniform, merge_weighted
    from reservoir.schema import (
        BuildableReservoir,
        Reservoir,
        WeightedItem,
        WeightedReservoir,
    )
    from reservoir.simulator import (
        uniform_stream,
        weighted_pairs,
        zipf_stream,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "BuildableReservoir": ("reservoir.schema", "BuildableReservoir"),
    "Reservoir": ("reservoir.schema", "Reservoir"),
    "WeightedItem": ("reservoir.schema", "WeightedItem"),
    "WeightedReservoir": ("reservoir.schema", "WeightedReservoir"),
    "add_l": ("reservoir.algorithms", "add_l"),
    "add_r": ("reservoir.algorithms", "add_r"),
    "add_weighted": ("reservoir.algorithms", "add_weighted"),
    "build_l": ("reservoir.algorithms", "build_l"),
    "build_r": ("reservoir.algorithms", "build_r"),
    "build_weighted": ("reservoir.algorithms", "build_weighted"),
    "dump_reservoirs": ("reservoir.io_jsonl", "dump_reservoirs"),
    "dump_weighted": ("reservoir.io_jsonl", "dump_weighted"),
    "freeze": ("reservoir.algorithms", "freeze"),
    "load_reservoirs": ("reservoir.io_jsonl", "load_reservoirs"),
    "load_weighted": ("reservoir.io_jsonl", "load_weighted"),
    "merge_uniform": ("reservoir.merge", "merge_uniform"),
    "merge_weighted": ("reservoir.merge", "merge_weighted"),
    "reservoir_from_dict": ("reservoir.io_jsonl", "reservoir_from_dict"),
    "reservoir_to_dict": ("reservoir.io_jsonl", "reservoir_to_dict"),
    "sample_l": ("reservoir.algorithms", "sample_l"),
    "sample_r": ("reservoir.algorithms", "sample_r"),
    "sample_weighted": ("reservoir.algorithms", "sample_weighted"),
    "thaw": ("reservoir.algorithms", "thaw"),
    "uniform_stream": ("reservoir.simulator", "uniform_stream"),
    "weighted_from_dict": ("reservoir.io_jsonl", "weighted_from_dict"),
    "weighted_pairs": ("reservoir.simulator", "weighted_pairs"),
    "weighted_to_dict": ("reservoir.io_jsonl", "weighted_to_dict"),
    "zipf_stream": ("reservoir.simulator", "zipf_stream"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BuildableReservoir",
    "Reservoir",
    "WeightedItem",
    "WeightedReservoir",
    "__version__",
    "add_l",
    "add_r",
    "add_weighted",
    "build_l",
    "build_r",
    "build_weighted",
    "dump_reservoirs",
    "dump_weighted",
    "freeze",
    "load_reservoirs",
    "load_weighted",
    "merge_uniform",
    "merge_weighted",
    "reservoir_from_dict",
    "reservoir_to_dict",
    "sample_l",
    "sample_r",
    "sample_weighted",
    "thaw",
    "uniform_stream",
    "weighted_from_dict",
    "weighted_pairs",
    "weighted_to_dict",
    "zipf_stream",
]
