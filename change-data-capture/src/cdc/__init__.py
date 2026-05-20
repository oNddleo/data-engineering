"""change-data-capture — Debezium-style CDC event toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from cdc.compact import compact, compact_to_inserts
    from cdc.diff import change_vector, columns_changed, is_no_op_update
    from cdc.io_jsonl import (
        change_vector_from_dict,
        change_vector_to_dict,
        dump_change_vectors,
        dump_events,
        dump_lineage,
        event_from_dict,
        event_to_dict,
        lineage_from_dict,
        lineage_to_dict,
        load_change_vectors,
        load_events,
        load_lineage,
        position_from_dict,
        position_to_dict,
    )
    from cdc.lineage import build_lineage
    from cdc.replay import apply_event, empty_snapshot, replay, replay_unordered
    from cdc.schema import (
        CDCEvent,
        ChangeVector,
        EventPosition,
        Op,
        RowLineage,
    )
    from cdc.simulator import generate


_LAZY: dict[str, tuple[str, str]] = {
    "CDCEvent": ("cdc.schema", "CDCEvent"),
    "ChangeVector": ("cdc.schema", "ChangeVector"),
    "EventPosition": ("cdc.schema", "EventPosition"),
    "Op": ("cdc.schema", "Op"),
    "RowLineage": ("cdc.schema", "RowLineage"),
    "apply_event": ("cdc.replay", "apply_event"),
    "build_lineage": ("cdc.lineage", "build_lineage"),
    "change_vector": ("cdc.diff", "change_vector"),
    "change_vector_from_dict": ("cdc.io_jsonl", "change_vector_from_dict"),
    "change_vector_to_dict": ("cdc.io_jsonl", "change_vector_to_dict"),
    "columns_changed": ("cdc.diff", "columns_changed"),
    "compact": ("cdc.compact", "compact"),
    "compact_to_inserts": ("cdc.compact", "compact_to_inserts"),
    "dump_change_vectors": ("cdc.io_jsonl", "dump_change_vectors"),
    "dump_events": ("cdc.io_jsonl", "dump_events"),
    "dump_lineage": ("cdc.io_jsonl", "dump_lineage"),
    "empty_snapshot": ("cdc.replay", "empty_snapshot"),
    "event_from_dict": ("cdc.io_jsonl", "event_from_dict"),
    "event_to_dict": ("cdc.io_jsonl", "event_to_dict"),
    "generate": ("cdc.simulator", "generate"),
    "is_no_op_update": ("cdc.diff", "is_no_op_update"),
    "lineage_from_dict": ("cdc.io_jsonl", "lineage_from_dict"),
    "lineage_to_dict": ("cdc.io_jsonl", "lineage_to_dict"),
    "load_change_vectors": ("cdc.io_jsonl", "load_change_vectors"),
    "load_events": ("cdc.io_jsonl", "load_events"),
    "load_lineage": ("cdc.io_jsonl", "load_lineage"),
    "position_from_dict": ("cdc.io_jsonl", "position_from_dict"),
    "position_to_dict": ("cdc.io_jsonl", "position_to_dict"),
    "replay": ("cdc.replay", "replay"),
    "replay_unordered": ("cdc.replay", "replay_unordered"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CDCEvent",
    "ChangeVector",
    "EventPosition",
    "Op",
    "RowLineage",
    "__version__",
    "apply_event",
    "build_lineage",
    "change_vector",
    "change_vector_from_dict",
    "change_vector_to_dict",
    "columns_changed",
    "compact",
    "compact_to_inserts",
    "dump_change_vectors",
    "dump_events",
    "dump_lineage",
    "empty_snapshot",
    "event_from_dict",
    "event_to_dict",
    "generate",
    "is_no_op_update",
    "lineage_from_dict",
    "lineage_to_dict",
    "load_change_vectors",
    "load_events",
    "load_lineage",
    "position_from_dict",
    "position_to_dict",
    "replay",
    "replay_unordered",
]
