"""Snapshot replay: apply_event + replay + replay_unordered."""

from __future__ import annotations

import pytest

from cdc.replay import apply_event, empty_snapshot, replay, replay_unordered
from cdc.schema import CDCEvent, Op

from ._fixtures import make_delete, make_insert, make_update, pos


def test_apply_insert_creates_row() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    assert ("users", "1") in snap


def test_apply_update_modifies_row() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    apply_event(snap, make_update())
    state, _ = snap[("users", "1")]
    assert state["age"] == 31


def test_apply_delete_tombstones_row() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    apply_event(snap, make_update())
    apply_event(snap, make_delete())
    # After replay-with-cleanup, the row should be gone.
    rows = replay([make_insert(), make_update(), make_delete()])
    assert ("users", "1") not in rows


def test_apply_rejects_duplicate_insert_strict() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    with pytest.raises(ValueError, match="already-existing"):
        apply_event(snap, make_insert(position=pos(offset=2)))


def test_apply_rejects_update_for_missing_row_strict() -> None:
    snap = empty_snapshot()
    with pytest.raises(ValueError, match="UPDATE for missing"):
        apply_event(snap, make_update())


def test_apply_rejects_delete_for_missing_row_strict() -> None:
    snap = empty_snapshot()
    with pytest.raises(ValueError, match="DELETE for missing"):
        apply_event(snap, make_delete())


def test_apply_lenient_drops_orphan_update() -> None:
    """In lenient mode, UPDATE-without-INSERT is treated as INSERT."""
    snap = empty_snapshot()
    apply_event(snap, make_update(), strict=False)
    assert ("users", "1") in snap


def test_apply_lenient_drops_orphan_delete() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_delete(), strict=False)
    # Lenient: no error, but row never existed.
    assert ("users", "1") not in snap


def test_apply_rejects_out_of_order() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())  # offset=1
    apply_event(snap, make_update(position=pos(offset=5)))  # current state
    # Strict mode: a stale UPDATE (older position) should be rejected.
    with pytest.raises(ValueError, match="newer"):
        apply_event(
            snap,
            make_update(
                position=pos(offset=3), before={"id": 1, "age": 30}, after={"id": 1, "age": 32}
            ),
        )


def test_apply_lenient_drops_out_of_order() -> None:
    """In lenient mode, a stale event silently no-ops."""
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    apply_event(snap, make_update())
    # Send a stale UPDATE.
    stale = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=500_000,
        position=pos(offset=0),
        before={"id": 1, "age": 30},
        after={"id": 1, "age": 99},
    )
    apply_event(snap, stale, strict=False)
    state, _ = snap[("users", "1")]
    # The current state remains at age 31 (not overwritten).
    assert state["age"] == 31


def test_replay_basic_lifecycle() -> None:
    rows = replay([make_insert(), make_update()])
    assert rows[("users", "1")]["age"] == 31


def test_replay_delete_removes_row() -> None:
    rows = replay([make_insert(), make_update(), make_delete()])
    assert ("users", "1") not in rows


def test_replay_unordered_sorts_first() -> None:
    """replay_unordered reorders by position before applying."""
    out_of_order = [make_update(), make_insert()]  # update first by arrival
    # Reverse positions would normally fail in strict mode...
    rows = replay_unordered(out_of_order, strict=True)
    assert rows[("users", "1")]["age"] == 31


def test_replay_multiple_rows() -> None:
    insert1 = make_insert()
    insert2 = make_insert(pk="2", after={"id": 2, "name": "Bob"}, position=pos(offset=2))
    rows = replay([insert1, insert2])
    assert ("users", "1") in rows
    assert ("users", "2") in rows


def test_replay_independent_tables() -> None:
    user_insert = make_insert()
    order_insert = make_insert(
        table="orders",
        pk="100",
        after={"id": 100, "total": 50000},
        position=pos(offset=2),
    )
    rows = replay([user_insert, order_insert])
    assert ("users", "1") in rows
    assert ("orders", "100") in rows


def test_replay_empty_input() -> None:
    assert replay([]) == {}


def test_apply_returns_state() -> None:
    """apply_event returns the new state of the row."""
    snap = empty_snapshot()
    result = apply_event(snap, make_insert())
    assert result == {"id": 1, "name": "Alice", "age": 30}


def test_apply_delete_returns_none() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    result = apply_event(snap, make_delete(position=pos(offset=2)))
    assert result is None


def test_apply_lenient_returns_existing_state_on_stale() -> None:
    snap = empty_snapshot()
    apply_event(snap, make_insert())
    apply_event(snap, make_update(position=pos(offset=5)))
    stale = make_update(
        position=pos(offset=3), before={"id": 1, "age": 30}, after={"id": 1, "age": 99}
    )
    result = apply_event(snap, stale, strict=False)
    # Should return the current (non-stale) state.
    assert result == {"id": 1, "name": "Alice", "age": 31}
