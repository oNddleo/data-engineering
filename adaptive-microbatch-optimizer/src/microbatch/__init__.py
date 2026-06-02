"""Adaptive micro-batch optimizer — PID-driven window sizing with backpressure."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "PIDConfig": "microbatch.pid",
        "PIDController": "microbatch.pid",
        "BackpressureMonitor": "microbatch.backpressure",
        "PressureSignal": "microbatch.backpressure",
        "SLAConfig": "microbatch.window",
        "WindowSnapshot": "microbatch.window",
        "AdaptiveWindowManager": "microbatch.window",
        "MetricsCollector": "microbatch.metrics",
        "BatchMetric": "microbatch.metrics",
        "LatencySnapshot": "microbatch.metrics",
        "ThroughputSnapshot": "microbatch.metrics",
        "MicroBatchProcessor": "microbatch.processor",
        "ProcessorStats": "microbatch.processor",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'microbatch' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)
