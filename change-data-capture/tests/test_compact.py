"""Log compaction tests."""

from __future__ import annotations

from cdc.compact import compact, compact_to_inserts
from cdc.replay import replay
from cdc.schema import Op

from ._fixtures import make_delete, make_insert, make_update, pos


def test_compact_single_insert() -> None:
    out = compact([make_insert()])
    assert len(out) == 1
    assert out[0].op is Op.CREATE


def test_compact_insert_plus_update_keeps_update() -> None:
    """A pure UPDATE survives; the INSERT is discarded."""
    out = compact([make_insert(), make_update()])
    assert len(out) == 1
    assert out[0].op is Op.UPDATE


def test_compact_insert_update_delete_collapses_to_delete() -> None:
    out = compact([make_insert(), make_update(), make_delete()])
    assert len(out) == 1
    assert out[0].op is Op.DELETE


def test_compact_orphan_delete_dropped() -> None:
    """A DELETE for a row we never INSERTed is dropped silently."""
    out = compact([make_delete()])
    assert out == []


def test_compact_recreation_after_delete() -> None:
    """INSERT → DELETE → INSERT (same PK) compacts to the latest INSERT."""
    events = [
        make_insert(position=pos(offset=1)),
        make_delete(position=pos(offset=2)),
        make_insert(
            position=pos(offset=3),
            ts_ms=4_000_000,
            after={"id": 1, "name": "Alice 2.0", "age": 25},
        ),
    ]
    out = compact(events)
    assert len(out) == 1
    assert out[0].op is Op.CREATE
    assert out[0].after["name"] == "Alice 2.0"


def test_compact_multiple_pks() -> None:
    e1 = make_insert(pk="1", after={"id": 1}, position=pos(offset=1))
    e2 = make_insert(pk="2", after={"id": 2}, position=pos(offset=2))
    e3 = make_insert(pk="3", after={"id": 3}, position=pos(offset=3))
    out = compact([e1, e2, e3])
    assert {e.pk for e in out} == {"1", "2", "3"}


def test_compact_replay_equivalence() -> None:
    """Replaying the compacted stream gives the same materialised state.

    Uses ``strict=False`` because the compacted form may contain a DELETE
    for a row that never had an INSERT/UPDATE in the compacted stream —
    that's expected when the original lifecycle ended in a DELETE.
    """
    events = [make_insert(), make_update(), make_delete()]
    full = replay(events, strict=False)
    compacted = compact(events)
    assert replay(compacted, strict=False) == full


def test_compact_preserves_position_order() -> None:
    """Surviving events come out in ascending position order."""
    e1 = make_insert(pk="A", after={"id": "A"}, position=pos(offset=10))
    e2 = make_insert(pk="B", after={"id": "B"}, position=pos(offset=5))
    out = compact([e1, e2])
    # B has smaller offset, should come first.
    assert out[0].pk == "B"
    assert out[1].pk == "A"


def test_compact_empty_input() -> None:
    assert compact([]) == []


def test_compact_to_inserts_rewrites_updates() -> None:
    out = compact_to_inserts([make_insert(), make_update()])
    assert len(out) == 1
    assert out[0].op is Op.CREATE
    # The "after" state matches the UPDATE's after.
    assert out[0].after["age"] == 31


def test_compact_to_inserts_preserves_deletes() -> None:
    out = compact_to_inserts([make_insert(), make_delete()])
    assert len(out) == 1
    assert out[0].op is Op.DELETE


def test_compact_reduces_size() -> None:
    """A multi-update stream compacts to one event per PK."""
    events = [make_insert()]
    for i in range(10):
        events.append(
            make_update(
                position=pos(offset=i + 2),
                ts_ms=1_000_000 + i,
                before={"id": 1, "name": "Alice", "age": 30 + i},
                after={"id": 1, "name": "Alice", "age": 31 + i},
            )
        )
    out = compact(events)
    assert len(out) == 1  # collapses to a single UPDATE
