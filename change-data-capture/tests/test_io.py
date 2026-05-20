"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from cdc.diff import change_vector
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
from cdc.schema import EventPosition, RowLineage

from ._fixtures import make_delete, make_insert, make_update, pos


def test_position_roundtrip() -> None:
    p = pos(offset=123)
    assert position_from_dict(position_to_dict(p)) == p


def test_event_insert_roundtrip() -> None:
    e = make_insert()
    assert event_from_dict(event_to_dict(e)) == e


def test_event_update_roundtrip() -> None:
    e = make_update()
    assert event_from_dict(event_to_dict(e)) == e


def test_event_delete_roundtrip() -> None:
    e = make_delete()
    assert event_from_dict(event_to_dict(e)) == e


def test_event_with_db_roundtrip() -> None:
    e = make_insert(db="shop")
    assert event_from_dict(event_to_dict(e)) == e


def test_dump_load_many_events() -> None:
    events = [make_insert(pk=str(i), after={"id": i}, position=pos(offset=i)) for i in range(1, 6)]
    assert load_events(dump_events(events)) == events


def test_change_vector_roundtrip() -> None:
    cv = change_vector(make_update())
    assert change_vector_from_dict(change_vector_to_dict(cv)) == cv


def test_lineage_roundtrip() -> None:
    rows = build_lineage([make_insert(), make_update()])
    out = load_lineage(dump_lineage(rows))
    assert out == rows


def test_lineage_with_deletion_roundtrip() -> None:
    r = RowLineage(
        table="users",
        pk="1",
        created_at_ms=1_000_000,
        last_modified_at_ms=3_000_000,
        n_updates=2,
        is_deleted=True,
    )
    assert lineage_from_dict(lineage_to_dict(r)) == r


def test_event_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_events("[1, 2, 3]\n")


def test_event_load_rejects_non_scalar_column() -> None:
    bad = (
        '{"op": "c", "table": "x", "pk": "1", "ts_ms": 0, '
        '"position": {"log_file": "f", "offset": 0}, '
        '"after": {"col": {"nested": "object"}}}\n'
    )
    with pytest.raises(TypeError, match="JSON scalar"):
        load_events(bad)


def test_event_load_rejects_bad_db_type() -> None:
    bad = (
        '{"op": "c", "table": "x", "pk": "1", "ts_ms": 0, '
        '"position": {"log_file": "f", "offset": 0}, '
        '"after": {"id": 1}, "db": 123}\n'
    )
    with pytest.raises(TypeError, match="db"):
        load_events(bad)


def test_lineage_load_rejects_non_bool_deleted() -> None:
    bad = (
        '{"table": "x", "pk": "1", '
        '"created_at_ms": 0, "last_modified_at_ms": 0, '
        '"n_updates": 0, "is_deleted": "yes"}\n'
    )
    with pytest.raises(TypeError, match="is_deleted"):
        load_lineage(bad)


def test_dump_skips_blank_lines() -> None:
    events = [make_insert()]
    text = "\n\n" + dump_events(events) + "\n\n"
    assert load_events(text) == events


def test_change_vector_dump_load_many() -> None:
    cvs = [
        change_vector(
            make_update(
                position=pos(offset=i),
                ts_ms=1_000 * i,
                before={"id": 1, "age": 30 + i},
                after={"id": 1, "age": 31 + i},
            )
        )
        for i in range(1, 4)
    ]
    assert load_change_vectors(dump_change_vectors(cvs)) == cvs


def test_position_rejects_negative_offset_via_io() -> None:
    """The codec must enforce the invariant after re-load."""
    bad = '{"log_file": "f", "offset": -5}'
    import json

    with pytest.raises(ValueError, match="offset"):
        position_from_dict(json.loads(bad))


def test_event_position_ordering_after_roundtrip() -> None:
    """Positions stay strictly ordered after JSONL round-trip."""
    a = EventPosition(log_file="binlog.000001", offset=10)
    b = EventPosition(log_file="binlog.000002", offset=5)
    assert position_from_dict(position_to_dict(a)) < position_from_dict(position_to_dict(b))
