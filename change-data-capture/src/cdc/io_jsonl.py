"""JSONL codec for CDCEvent / ChangeVector / RowLineage.

Each event renders as a Debezium-flavoured JSON envelope:

.. code:: json

    {"op": "u", "table": "orders", "pk": "42", "ts_ms": 1715251200000,
     "position": {"log_file": "binlog.000123", "offset": 4567},
     "db": "shop",
     "before": {"id": 42, "status": "pending"},
     "after":  {"id": 42, "status": "paid"}}
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cdc.schema import CDCEvent, ChangeVector, EventPosition, Op, RowLineage

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from cdc.schema import RowState


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_dict(d: dict[str, object], key: str) -> dict[str, object]:
    v = d[key]
    if not isinstance(v, dict):
        raise TypeError(f"{key} must be dict, got {type(v).__name__}")
    return v


def _opt_dict(d: dict[str, object], key: str) -> dict[str, object]:
    v = d.get(key, {})
    if not isinstance(v, dict):
        raise TypeError(f"{key} must be dict, got {type(v).__name__}")
    return v


def _validate_row_state(v: dict[str, object], where: str) -> RowState:
    out: RowState = {}
    for k, val in v.items():
        if val is None:
            out[k] = None
        elif isinstance(val, bool | int | float | str):
            # bool must be checked first since bool is a subclass of int.
            out[k] = val
        else:
            raise TypeError(
                f"{where}[{k!r}] must be JSON scalar, got {type(val).__name__}",
            )
    return out


# ---------- EventPosition --------------------------------------------------


def position_to_dict(p: EventPosition) -> dict[str, object]:
    return {"log_file": p.log_file, "offset": p.offset}


def position_from_dict(d: dict[str, object]) -> EventPosition:
    return EventPosition(
        log_file=_require_str(d, "log_file"),
        offset=_require_int(d, "offset"),
    )


# ---------- CDCEvent -------------------------------------------------------


def event_to_dict(e: CDCEvent) -> dict[str, object]:
    out: dict[str, object] = {
        "op": e.op.value,
        "table": e.table,
        "pk": e.pk,
        "ts_ms": e.ts_ms,
        "position": position_to_dict(e.position),
    }
    if e.db:
        out["db"] = e.db
    if e.before:
        out["before"] = dict(e.before)
    if e.after:
        out["after"] = dict(e.after)
    return out


def event_from_dict(d: dict[str, object]) -> CDCEvent:
    position = position_from_dict(_require_dict(d, "position"))
    before = _validate_row_state(_opt_dict(d, "before"), "before")
    after = _validate_row_state(_opt_dict(d, "after"), "after")
    return CDCEvent(
        op=Op(_require_str(d, "op")),
        table=_require_str(d, "table"),
        pk=_require_str(d, "pk"),
        ts_ms=_require_int(d, "ts_ms"),
        position=position,
        before=before,
        after=after,
        db=_db_field(d),
    )


def _db_field(d: dict[str, object]) -> str:
    """Extract optional db field, defaulting to ''."""
    v = d.get("db", "")
    if not isinstance(v, str):
        raise TypeError(f"db must be str, got {type(v).__name__}")
    return v


# ---------- ChangeVector ---------------------------------------------------


def change_vector_to_dict(c: ChangeVector) -> dict[str, object]:
    return {
        "table": c.table,
        "pk": c.pk,
        "before_values": dict(c.before_values),
        "after_values": dict(c.after_values),
    }


def change_vector_from_dict(d: dict[str, object]) -> ChangeVector:
    return ChangeVector(
        table=_require_str(d, "table"),
        pk=_require_str(d, "pk"),
        before_values=_validate_row_state(
            _opt_dict(d, "before_values"),
            "before_values",
        ),
        after_values=_validate_row_state(
            _opt_dict(d, "after_values"),
            "after_values",
        ),
    )


# ---------- RowLineage -----------------------------------------------------


def lineage_to_dict(l: RowLineage) -> dict[str, object]:  # noqa: E741 — l is a clean param name
    return {
        "table": l.table,
        "pk": l.pk,
        "created_at_ms": l.created_at_ms,
        "last_modified_at_ms": l.last_modified_at_ms,
        "n_updates": l.n_updates,
        "is_deleted": l.is_deleted,
    }


def lineage_from_dict(d: dict[str, object]) -> RowLineage:
    raw_deleted = d["is_deleted"]
    if not isinstance(raw_deleted, bool):
        raise TypeError(
            f"is_deleted must be bool, got {type(raw_deleted).__name__}",
        )
    return RowLineage(
        table=_require_str(d, "table"),
        pk=_require_str(d, "pk"),
        created_at_ms=_require_int(d, "created_at_ms"),
        last_modified_at_ms=_require_int(d, "last_modified_at_ms"),
        n_updates=_require_int(d, "n_updates"),
        is_deleted=raw_deleted,
    )


# ---------- dump / load ----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[CDCEvent]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_change_vectors(items: Iterable[ChangeVector]) -> str:
    return _dump(change_vector_to_dict(c) for c in items)


def dump_lineage(items: Iterable[RowLineage]) -> str:
    return _dump(lineage_to_dict(r) for r in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_events(text: str) -> list[CDCEvent]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_change_vectors(text: str) -> list[ChangeVector]:
    return [change_vector_from_dict(d) for d in _iter_lines(text)]


def load_lineage(text: str) -> list[RowLineage]:
    return [lineage_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "change_vector_from_dict",
    "change_vector_to_dict",
    "dump_change_vectors",
    "dump_events",
    "dump_lineage",
    "event_from_dict",
    "event_to_dict",
    "lineage_from_dict",
    "lineage_to_dict",
    "load_change_vectors",
    "load_events",
    "load_lineage",
    "position_from_dict",
    "position_to_dict",
]
