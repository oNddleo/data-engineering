"""Lineage builder."""

from __future__ import annotations

from cdc.lineage import build_lineage

from ._fixtures import make_delete, make_insert, make_update, pos


def test_lineage_single_insert() -> None:
    rows = build_lineage([make_insert()])
    assert len(rows) == 1
    assert rows[0].n_updates == 0
    assert rows[0].is_deleted is False


def test_lineage_counts_updates() -> None:
    events = [make_insert()]
    for i in range(3):
        events.append(
            make_update(
                position=pos(offset=i + 2),
                ts_ms=1_000_000 + i,
                before={"id": 1, "age": 30 + i},
                after={"id": 1, "age": 31 + i},
            )
        )
    rows = build_lineage(events)
    assert rows[0].n_updates == 3


def test_lineage_tracks_delete() -> None:
    rows = build_lineage([make_insert(), make_delete(position=pos(offset=2))])
    assert rows[0].is_deleted is True


def test_lineage_timestamps_track_first_and_last() -> None:
    events = [
        make_insert(ts_ms=1_000),
        make_update(ts_ms=5_000, position=pos(offset=2)),
        make_update(
            ts_ms=10_000,
            position=pos(offset=3),
            before={"id": 1, "age": 31},
            after={"id": 1, "age": 32},
        ),
    ]
    rows = build_lineage(events)
    assert rows[0].created_at_ms == 1_000
    assert rows[0].last_modified_at_ms == 10_000


def test_lineage_orphan_update_skipped() -> None:
    """An UPDATE-without-CREATE is silently skipped."""
    rows = build_lineage([make_update()])
    assert rows == []


def test_lineage_orphan_delete_skipped() -> None:
    rows = build_lineage([make_delete()])
    assert rows == []


def test_lineage_multiple_rows() -> None:
    e1 = make_insert(pk="1", after={"id": 1}, position=pos(offset=1))
    e2 = make_insert(pk="2", after={"id": 2}, position=pos(offset=2))
    rows = build_lineage([e1, e2])
    assert len(rows) == 2
    assert {r.pk for r in rows} == {"1", "2"}


def test_lineage_sorted_by_table_pk() -> None:
    e1 = make_insert(pk="Z", after={"id": "Z"}, position=pos(offset=1))
    e2 = make_insert(pk="A", after={"id": "A"}, position=pos(offset=2))
    rows = build_lineage([e1, e2])
    assert [r.pk for r in rows] == ["A", "Z"]


def test_lineage_sorted_across_tables() -> None:
    e_user = make_insert(table="users", pk="1", position=pos(offset=2))
    e_order = make_insert(
        table="orders",
        pk="1",
        after={"id": 1, "total": 50000},
        position=pos(offset=1),
    )
    rows = build_lineage([e_user, e_order])
    assert [r.table for r in rows] == ["orders", "users"]


def test_lineage_empty_input() -> None:
    assert build_lineage([]) == []


def test_lineage_read_event_creates_row() -> None:
    """A READ (initial-snapshot) event counts as a creation."""
    from cdc.schema import CDCEvent, Op

    read_event = CDCEvent(
        op=Op.READ,
        table="users",
        pk="1",
        ts_ms=500_000,
        position=pos(offset=0),
        after={"id": 1, "name": "Alice"},
    )
    rows = build_lineage([read_event])
    assert len(rows) == 1
    assert rows[0].created_at_ms == 500_000
