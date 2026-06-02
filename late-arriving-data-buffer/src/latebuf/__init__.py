"""late-arriving-data-buffer — event-time buffer with watermarks."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "BufferConfig": ("latebuf.schema", "BufferConfig"),
        "BufferStats": ("latebuf.schema", "BufferStats"),
        "EmittedRecord": ("latebuf.schema", "EmittedRecord"),
        "Event": ("latebuf.schema", "Event"),
        "EventDisposition": ("latebuf.schema", "EventDisposition"),
        "LateArrivingBuffer": ("latebuf.buffer", "LateArrivingBuffer"),
        "LatenessDistribution": ("latebuf.simulator", "LatenessDistribution"),
        "VN_TZ": ("latebuf.schema", "VN_TZ"),
        "WatermarkState": ("latebuf.watermark", "WatermarkState"),
        "WatermarkStrategy": ("latebuf.schema", "WatermarkStrategy"),
        "compute_stats": ("latebuf.metrics", "compute_stats"),
        "dump_emitted": ("latebuf.io_jsonl", "dump_emitted"),
        "dump_events": ("latebuf.io_jsonl", "dump_events"),
        "emitted_from_dict": ("latebuf.io_jsonl", "emitted_from_dict"),
        "emitted_to_dict": ("latebuf.io_jsonl", "emitted_to_dict"),
        "event_from_dict": ("latebuf.io_jsonl", "event_from_dict"),
        "event_to_dict": ("latebuf.io_jsonl", "event_to_dict"),
        "generate": ("latebuf.simulator", "generate"),
        "load_emitted": ("latebuf.io_jsonl", "load_emitted"),
        "load_events": ("latebuf.io_jsonl", "load_events"),
        "new_watermark": ("latebuf.watermark", "new_watermark"),
        "stats_from_dict": ("latebuf.io_jsonl", "stats_from_dict"),
        "stats_to_dict": ("latebuf.io_jsonl", "stats_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BufferConfig",
    "BufferStats",
    "EmittedRecord",
    "Event",
    "EventDisposition",
    "LateArrivingBuffer",
    "LatenessDistribution",
    "VN_TZ",
    "WatermarkState",
    "WatermarkStrategy",
    "__version__",
    "compute_stats",
    "dump_emitted",
    "dump_events",
    "emitted_from_dict",
    "emitted_to_dict",
    "event_from_dict",
    "event_to_dict",
    "generate",
    "load_emitted",
    "load_events",
    "new_watermark",
    "stats_from_dict",
    "stats_to_dict",
]
