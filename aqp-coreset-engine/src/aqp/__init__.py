"""aqp-coreset-engine — approximate query processing via coresets."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Coreset": ("aqp.coreset.core", "Coreset"),
        "WeightedRow": ("aqp.coreset.core", "WeightedRow"),
        "SensitivityCoreset": ("aqp.coreset.sensitivity", "SensitivityCoreset"),
        "UniformCoreset": ("aqp.coreset.uniform", "UniformCoreset"),
        "StreamingSumCoreset": ("aqp.coreset.streaming", "StreamingSumCoreset"),
        "KLLSketch": ("aqp.coreset.kll", "KLLSketch"),
        "coreset_size_sum": ("aqp.bounds.size", "coreset_size_sum"),
        "hoeffding_count_size": ("aqp.bounds.size", "hoeffding_count_size"),
        "Predicate": ("aqp.queries.predicates", "Predicate"),
        "eq_pred": ("aqp.queries.predicates", "eq_pred"),
        "range_pred": ("aqp.queries.predicates", "range_pred"),
        "box_pred": ("aqp.queries.predicates", "box_pred"),
        "and_": ("aqp.queries.predicates", "and_"),
        "validate_coverage": ("aqp.eval", "validate_coverage"),
        "ValidationReport": ("aqp.eval", "ValidationReport"),
    }

    if name in _LAZY:
        from importlib import import_module

        module, attr = _LAZY[name]
        return getattr(import_module(module), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Coreset",
    "KLLSketch",
    "Predicate",
    "SensitivityCoreset",
    "StreamingSumCoreset",
    "UniformCoreset",
    "ValidationReport",
    "WeightedRow",
    "__version__",
    "and_",
    "box_pred",
    "coreset_size_sum",
    "eq_pred",
    "hoeffding_count_size",
    "range_pred",
    "validate_coverage",
]
