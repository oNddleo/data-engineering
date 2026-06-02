"""postgres-vs-clickhouse-benchmark — cross-engine query benchmark harness."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Query": ("pvc.workloads.base", "Query"),
        "Workload": ("pvc.workloads.base", "Workload"),
        "TPCH_QUERIES": ("pvc.workloads.tpch", "TPCH_QUERIES"),
        "NY_TAXI_QUERIES": ("pvc.workloads.nytaxi", "NY_TAXI_QUERIES"),
        "Engine": ("pvc.engines.base", "Engine"),
        "EngineError": ("pvc.engines.base", "EngineError"),
        "SQLiteEngine": ("pvc.engines.sqlite", "SQLiteEngine"),
        "InjectableEngine": ("pvc.engines.injectable", "InjectableEngine"),
        "LatencyStats": ("pvc.stats", "LatencyStats"),
        "summarise": ("pvc.stats", "summarise"),
        "BenchmarkRunner": ("pvc.benchmark", "BenchmarkRunner"),
        "QueryResult": ("pvc.benchmark", "QueryResult"),
        "IterationResult": ("pvc.benchmark", "IterationResult"),
        "ComparisonReport": ("pvc.report", "ComparisonReport"),
        "ReportRow": ("pvc.report", "ReportRow"),
        "build_comparison": ("pvc.report", "build_comparison"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "NY_TAXI_QUERIES",
    "TPCH_QUERIES",
    "BenchmarkRunner",
    "ComparisonReport",
    "Engine",
    "EngineError",
    "InjectableEngine",
    "IterationResult",
    "LatencyStats",
    "Query",
    "QueryResult",
    "ReportRow",
    "SQLiteEngine",
    "Workload",
    "__version__",
    "build_comparison",
    "summarise",
]
