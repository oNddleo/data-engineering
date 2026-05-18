"""column-statistics-collector — single-pass column profiler + drift detection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from colstats.categorical import SpaceSaving, cardinality, top_k
    from colstats.drift import ks, psi, psi_band
    from colstats.histogram import equi_depth, equi_width, maxdiff, reproject
    from colstats.io_jsonl import (
        dump_profiles,
        load_profiles,
        profile_from_dict,
        profile_to_dict,
    )
    from colstats.numeric import WelfordAccumulator, numeric_stats
    from colstats.profile import collect_profile
    from colstats.schema import (
        Bin,
        ColumnKind,
        ColumnProfile,
        Histogram,
        HistogramKind,
        NumericStats,
        StringStats,
        TopKEntry,
    )
    from colstats.simulator import (
        NumericShape,
        generate_categorical,
        generate_date,
        generate_numeric,
        generate_string,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "Bin": ("colstats.schema", "Bin"),
    "ColumnKind": ("colstats.schema", "ColumnKind"),
    "ColumnProfile": ("colstats.schema", "ColumnProfile"),
    "Histogram": ("colstats.schema", "Histogram"),
    "HistogramKind": ("colstats.schema", "HistogramKind"),
    "NumericShape": ("colstats.simulator", "NumericShape"),
    "NumericStats": ("colstats.schema", "NumericStats"),
    "SpaceSaving": ("colstats.categorical", "SpaceSaving"),
    "StringStats": ("colstats.schema", "StringStats"),
    "TopKEntry": ("colstats.schema", "TopKEntry"),
    "WelfordAccumulator": ("colstats.numeric", "WelfordAccumulator"),
    "cardinality": ("colstats.categorical", "cardinality"),
    "collect_profile": ("colstats.profile", "collect_profile"),
    "dump_profiles": ("colstats.io_jsonl", "dump_profiles"),
    "equi_depth": ("colstats.histogram", "equi_depth"),
    "equi_width": ("colstats.histogram", "equi_width"),
    "generate_categorical": ("colstats.simulator", "generate_categorical"),
    "generate_date": ("colstats.simulator", "generate_date"),
    "generate_numeric": ("colstats.simulator", "generate_numeric"),
    "generate_string": ("colstats.simulator", "generate_string"),
    "ks": ("colstats.drift", "ks"),
    "load_profiles": ("colstats.io_jsonl", "load_profiles"),
    "maxdiff": ("colstats.histogram", "maxdiff"),
    "numeric_stats": ("colstats.numeric", "numeric_stats"),
    "profile_from_dict": ("colstats.io_jsonl", "profile_from_dict"),
    "profile_to_dict": ("colstats.io_jsonl", "profile_to_dict"),
    "psi": ("colstats.drift", "psi"),
    "psi_band": ("colstats.drift", "psi_band"),
    "reproject": ("colstats.histogram", "reproject"),
    "top_k": ("colstats.categorical", "top_k"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Bin",
    "ColumnKind",
    "ColumnProfile",
    "Histogram",
    "HistogramKind",
    "NumericShape",
    "NumericStats",
    "SpaceSaving",
    "StringStats",
    "TopKEntry",
    "WelfordAccumulator",
    "__version__",
    "cardinality",
    "collect_profile",
    "dump_profiles",
    "equi_depth",
    "equi_width",
    "generate_categorical",
    "generate_date",
    "generate_numeric",
    "generate_string",
    "ks",
    "load_profiles",
    "maxdiff",
    "numeric_stats",
    "profile_from_dict",
    "profile_to_dict",
    "psi",
    "psi_band",
    "reproject",
    "top_k",
]
