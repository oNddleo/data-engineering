"""time-window-aggregator — tumbling / sliding / session windowing."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Event": ("windows.schema", "Event"),
        "Window": ("windows.schema", "Window"),
        "WindowKind": ("windows.schema", "WindowKind"),
        "WindowedAggregate": ("windows.schema", "WindowedAggregate"),
        "agg_from_dict": ("windows.io_jsonl", "agg_from_dict"),
        "agg_to_dict": ("windows.io_jsonl", "agg_to_dict"),
        "assign_window": ("windows.tumbling", "assign_window"),
        "bursty_stream": ("windows.simulator", "bursty_stream"),
        "dump_aggs": ("windows.io_jsonl", "dump_aggs"),
        "dump_events": ("windows.io_jsonl", "dump_events"),
        "event_from_dict": ("windows.io_jsonl", "event_from_dict"),
        "event_to_dict": ("windows.io_jsonl", "event_to_dict"),
        "load_aggs": ("windows.io_jsonl", "load_aggs"),
        "load_events": ("windows.io_jsonl", "load_events"),
        "session_aggregate": ("windows.session", "aggregate"),
        "sliding_aggregate": ("windows.sliding", "aggregate"),
        "tumbling_aggregate": ("windows.tumbling", "aggregate"),
        "uniform_stream": ("windows.simulator", "uniform_stream"),
        "window_from_dict": ("windows.io_jsonl", "window_from_dict"),
        "window_to_dict": ("windows.io_jsonl", "window_to_dict"),
        "windows_for": ("windows.sliding", "windows_for"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Event",
    "Window",
    "WindowKind",
    "WindowedAggregate",
    "__version__",
    "agg_from_dict",
    "agg_to_dict",
    "assign_window",
    "bursty_stream",
    "dump_aggs",
    "dump_events",
    "event_from_dict",
    "event_to_dict",
    "load_aggs",
    "load_events",
    "session_aggregate",
    "sliding_aggregate",
    "tumbling_aggregate",
    "uniform_stream",
    "window_from_dict",
    "window_to_dict",
    "windows_for",
]
