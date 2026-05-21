"""streaming-ingestion-replay-engine — Kafka-style replay with on-the-fly transforms."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Record": ("sire.log.record", "Record"),
        "RecordHeader": ("sire.log.record", "RecordHeader"),
        "Segment": ("sire.log.segment", "Segment"),
        "SegmentError": ("sire.log.segment", "SegmentError"),
        "Topic": ("sire.log.topic", "Topic"),
        "Cursor": ("sire.log.cursor", "Cursor"),
        "EndOfLog": ("sire.log.cursor", "EndOfLog"),
        "OffsetStore": ("sire.offsets", "OffsetStore"),
        "ReplayEngine": ("sire.replay", "ReplayEngine"),
        "ReplayPosition": ("sire.replay", "ReplayPosition"),
        "Transform": ("sire.transforms.base", "Transform"),
        "Mapper": ("sire.transforms.mapper", "Mapper"),
        "Filter": ("sire.transforms.filter", "Filter"),
        "ComposedTransform": ("sire.transforms.composed", "ComposedTransform"),
        "Sink": ("sire.sinks.base", "Sink"),
        "CollectingSink": ("sire.sinks.collect", "CollectingSink"),
        "JsonlFileSink": ("sire.sinks.file", "JsonlFileSink"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CollectingSink",
    "ComposedTransform",
    "Cursor",
    "EndOfLog",
    "Filter",
    "JsonlFileSink",
    "Mapper",
    "OffsetStore",
    "Record",
    "RecordHeader",
    "ReplayEngine",
    "ReplayPosition",
    "Segment",
    "SegmentError",
    "Sink",
    "Topic",
    "Transform",
    "__version__",
]
