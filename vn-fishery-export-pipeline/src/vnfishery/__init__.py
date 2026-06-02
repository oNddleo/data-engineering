"""vn-fishery-export-pipeline — VN seafood export aggregation."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "ExportRecord": ("vnfishery.schema", "ExportRecord"),
        "Form": ("vnfishery.schema", "Form"),
        "Grade": ("vnfishery.schema", "Grade"),
        "Market": ("vnfishery.schema", "Market"),
        "Species": ("vnfishery.schema", "Species"),
        "Aggregate": ("vnfishery.aggregate", "Aggregate"),
        "aggregate_by_species": ("vnfishery.aggregate", "aggregate_by_species"),
        "aggregate_by_market": ("vnfishery.aggregate", "aggregate_by_market"),
        "aggregate_by_species_market": (
            "vnfishery.aggregate",
            "aggregate_by_species_market",
        ),
        "aggregate_by_exporter": ("vnfishery.aggregate", "aggregate_by_exporter"),
        "benchmark_usd_cents_per_kg": (
            "vnfishery.benchmark",
            "benchmark_usd_cents_per_kg",
        ),
        "is_dumping_risk": ("vnfishery.benchmark", "is_dumping_risk"),
        "generate": ("vnfishery.simulator", "generate"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Aggregate",
    "ExportRecord",
    "Form",
    "Grade",
    "Market",
    "Species",
    "__version__",
    "aggregate_by_exporter",
    "aggregate_by_market",
    "aggregate_by_species",
    "aggregate_by_species_market",
    "benchmark_usd_cents_per_kg",
    "generate",
    "is_dumping_risk",
]
