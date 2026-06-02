"""flash-sale-event-pipeline — watermark + tumbling window + hotness detectors."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Event": ("flashpipe.events", "Event"),
        "EventKind": ("flashpipe.events", "EventKind"),
        "HotnessEvent": ("flashpipe.detectors", "HotnessEvent"),
        "HotnessKind": ("flashpipe.detectors", "HotnessKind"),
        "HotnessSink": ("flashpipe.sinks", "HotnessSink"),
        "InMemoryHotnessSink": ("flashpipe.sinks", "InMemoryHotnessSink"),
        "InMemoryWindowSink": ("flashpipe.sinks", "InMemoryWindowSink"),
        "MetricsCollector": ("flashpipe.metrics", "MetricsCollector"),
        "MetricsSnapshot": ("flashpipe.metrics", "MetricsSnapshot"),
        "StampedeDetector": ("flashpipe.detectors", "StampedeDetector"),
        "StreamEngine": ("flashpipe.engine", "StreamEngine"),
        "TumblingAggregator": ("flashpipe.windows", "TumblingAggregator"),
        "VN_TZ": ("flashpipe.events", "VN_TZ"),
        "WatermarkTracker": ("flashpipe.watermark", "WatermarkTracker"),
        "WindowAggregate": ("flashpipe.windows", "WindowAggregate"),
        "WindowSink": ("flashpipe.sinks", "WindowSink"),
        "WindowState": ("flashpipe.windows", "WindowState"),
        "aggregate_to_dict": ("flashpipe.io_jsonl", "aggregate_to_dict"),
        "detect_burndown": ("flashpipe.detectors", "detect_burndown"),
        "detect_hot_product": ("flashpipe.detectors", "detect_hot_product"),
        "dump_aggregates": ("flashpipe.io_jsonl", "dump_aggregates"),
        "dump_events": ("flashpipe.io_jsonl", "dump_events"),
        "dump_hotness": ("flashpipe.io_jsonl", "dump_hotness"),
        "event_from_dict": ("flashpipe.io_jsonl", "event_from_dict"),
        "event_to_dict": ("flashpipe.io_jsonl", "event_to_dict"),
        "generate": ("flashpipe.simulator", "generate"),
        "hotness_from_dict": ("flashpipe.io_jsonl", "hotness_from_dict"),
        "hotness_to_dict": ("flashpipe.io_jsonl", "hotness_to_dict"),
        "load_events": ("flashpipe.io_jsonl", "load_events"),
        "window_start_for": ("flashpipe.windows", "window_start_for"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VN_TZ",
    "Event",
    "EventKind",
    "HotnessEvent",
    "HotnessKind",
    "HotnessSink",
    "InMemoryHotnessSink",
    "InMemoryWindowSink",
    "MetricsCollector",
    "MetricsSnapshot",
    "StampedeDetector",
    "StreamEngine",
    "TumblingAggregator",
    "WatermarkTracker",
    "WindowAggregate",
    "WindowSink",
    "WindowState",
    "__version__",
    "aggregate_to_dict",
    "detect_burndown",
    "detect_hot_product",
    "dump_aggregates",
    "dump_events",
    "dump_hotness",
    "event_from_dict",
    "event_to_dict",
    "generate",
    "hotness_from_dict",
    "hotness_to_dict",
    "load_events",
    "window_start_for",
]
