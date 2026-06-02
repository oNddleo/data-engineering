"""Test fixtures: CDC event builders."""

from __future__ import annotations

from typing import Any

from cdc.schema import CDCEvent, EventPosition, Op


def pos(log_file: str = "binlog.000001", offset: int = 1) -> EventPosition:
    return EventPosition(log_file=log_file, offset=offset)


def make_insert(**overrides: Any) -> CDCEvent:
    defaults: dict[str, Any] = {
        "op": Op.CREATE,
        "table": "users",
        "pk": "1",
        "ts_ms": 1_000_000,
        "position": pos(offset=1),
        "after": {"id": 1, "name": "Alice", "age": 30},
    }
    defaults.update(overrides)
    return CDCEvent(**defaults)


def make_update(**overrides: Any) -> CDCEvent:
    defaults: dict[str, Any] = {
        "op": Op.UPDATE,
        "table": "users",
        "pk": "1",
        "ts_ms": 2_000_000,
        "position": pos(offset=2),
        "before": {"id": 1, "name": "Alice", "age": 30},
        "after": {"id": 1, "name": "Alice", "age": 31},
    }
    defaults.update(overrides)
    return CDCEvent(**defaults)


def make_delete(**overrides: Any) -> CDCEvent:
    defaults: dict[str, Any] = {
        "op": Op.DELETE,
        "table": "users",
        "pk": "1",
        "ts_ms": 3_000_000,
        "position": pos(offset=3),
        "before": {"id": 1, "name": "Alice", "age": 31},
    }
    defaults.update(overrides)
    return CDCEvent(**defaults)


__all__ = ["make_delete", "make_insert", "make_update", "pos"]
