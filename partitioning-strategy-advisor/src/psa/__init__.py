"""partitioning-strategy-advisor — recommend partition + bucketing from query log."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "ParsedQuery": ("psa.parser", "ParsedQuery"),
        "parse_query": ("psa.parser", "parse_query"),
        "ColumnUsage": ("psa.profile", "ColumnUsage"),
        "QueryProfile": ("psa.profile", "QueryProfile"),
        "Profiler": ("psa.profile", "Profiler"),
        "CardinalityEstimate": ("psa.cardinality", "CardinalityEstimate"),
        "estimate_cardinality": ("psa.cardinality", "estimate_cardinality"),
        "SkewReport": ("psa.skew", "SkewReport"),
        "detect_skew": ("psa.skew", "detect_skew"),
        "PartitionRecommendation": ("psa.recommender", "PartitionRecommendation"),
        "BucketRecommendation": ("psa.recommender", "BucketRecommendation"),
        "recommend": ("psa.recommender", "recommend"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BucketRecommendation",
    "CardinalityEstimate",
    "ColumnUsage",
    "ParsedQuery",
    "PartitionRecommendation",
    "Profiler",
    "QueryProfile",
    "SkewReport",
    "__version__",
    "detect_skew",
    "estimate_cardinality",
    "parse_query",
    "recommend",
]
