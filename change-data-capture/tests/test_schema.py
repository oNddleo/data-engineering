"""Schema invariants: CDCEvent, EventPosition, ChangeVector, RowLineage."""

from __future__ import annotations

import pytest

from cdc.schema import CDCEvent, ChangeVector, EventPosition, Op, RowLineage

from ._fixtures import make_delete, make_insert, make_update, pos

# ---------- EventPosition --------------------------------------------------


def test_position_ordering() -> None:
    a = EventPosition(log_file="binlog.000001", offset=10)
    b = EventPosition(log_file="binlog.000001", offset=20)
    assert a < b
    assert a <= b
    assert not (b < a)


def test_position_cross_file_ordering() -> None:
    """binlog.000001 < binlog.000002 by lexicographic file order."""
    a = EventPosition(log_file="binlog.000001", offset=999_999)
    b = EventPosition(log_file="binlog.000002", offset=1)
    assert a < b


def test_position_rejects_negative_offset() -> None:
    with pytest.raises(ValueError, match="offset"):
        EventPosition(log_file="binlog.000001", offset=-1)


def test_position_zero_offset_allowed() -> None:
    """Offset 0 is valid (start of log)."""
    p = EventPosition(log_file="binlog.000001", offset=0)
    assert p.offset == 0


# ---------- CDCEvent INSERT / CREATE ---------------------------------------


def test_insert_basic() -> None:
    e = make_insert()
    assert e.op is Op.CREATE
    assert e.before == {}
    assert e.after == {"id": 1, "name": "Alice", "age": 30}


def test_insert_rejects_non_empty_before() -> None:
    with pytest.raises(ValueError, match="empty before"):
        make_insert(before={"id": 1})


def test_insert_rejects_empty_after() -> None:
    with pytest.raises(ValueError, match="non-empty after"):
        make_insert(after={})


# ---------- CDCEvent UPDATE ------------------------------------------------


def test_update_basic() -> None:
    e = make_update()
    assert e.op is Op.UPDATE
    assert e.before["age"] == 30
    assert e.after["age"] == 31


def test_update_rejects_empty_before() -> None:
    with pytest.raises(ValueError, match="non-empty before"):
        make_update(before={})


def test_update_rejects_empty_after() -> None:
    with pytest.raises(ValueError, match="non-empty after"):
        make_update(after={})


# ---------- CDCEvent DELETE ------------------------------------------------


def test_delete_basic() -> None:
    e = make_delete()
    assert e.op is Op.DELETE
    assert e.before == {"id": 1, "name": "Alice", "age": 31}
    assert e.after == {}


def test_delete_rejects_non_empty_after() -> None:
    with pytest.raises(ValueError, match="empty after"):
        make_delete(after={"id": 1})


def test_delete_rejects_empty_before() -> None:
    with pytest.raises(ValueError, match="non-empty before"):
        make_delete(before={})


# ---------- READ (snapshot) ------------------------------------------------


def test_read_event_basic() -> None:
    e = CDCEvent(
        op=Op.READ,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        after={"id": 1, "name": "Alice"},
    )
    assert e.op is Op.READ


def test_read_rejects_before() -> None:
    """READ events come from initial snapshots — they have no before state."""
    with pytest.raises(ValueError, match="empty before"):
        CDCEvent(
            op=Op.READ,
            table="users",
            pk="1",
            ts_ms=1_000_000,
            position=pos(offset=1),
            before={"id": 1},
            after={"id": 1},
        )


# ---------- General invariants ---------------------------------------------


def test_event_rejects_empty_table() -> None:
    with pytest.raises(ValueError, match="table"):
        make_insert(table="")


def test_event_rejects_empty_pk() -> None:
    with pytest.raises(ValueError, match="pk"):
        make_insert(pk="")


def test_event_rejects_negative_ts() -> None:
    with pytest.raises(ValueError, match="ts_ms"):
        make_insert(ts_ms=-1)


def test_op_values_complete() -> None:
    assert {o.value for o in Op} == {"c", "u", "d", "r"}


# ---------- ChangeVector ---------------------------------------------------


def test_change_vector_basic() -> None:
    cv = ChangeVector(
        table="users",
        pk="1",
        before_values={"age": 30},
        after_values={"age": 31},
    )
    assert cv.changed_columns == ("age",)


def test_change_vector_no_op() -> None:
    cv = ChangeVector(
        table="users",
        pk="1",
        before_values={},
        after_values={},
    )
    assert cv.is_no_op


def test_change_vector_rejects_mismatched_columns() -> None:
    with pytest.raises(ValueError, match="same column set"):
        ChangeVector(
            table="users",
            pk="1",
            before_values={"age": 30},
            after_values={"name": "Bob"},
        )


def test_change_vector_sorted_column_names() -> None:
    cv = ChangeVector(
        table="users",
        pk="1",
        before_values={"z": 1, "a": 2, "m": 3},
        after_values={"z": 4, "a": 5, "m": 6},
    )
    assert cv.changed_columns == ("a", "m", "z")


# ---------- RowLineage -----------------------------------------------------


def test_row_lineage_basic() -> None:
    r = RowLineage(
        table="users",
        pk="1",
        created_at_ms=1_000_000,
        last_modified_at_ms=2_000_000,
        n_updates=3,
        is_deleted=False,
    )
    assert r.n_updates == 3


def test_row_lineage_rejects_inverted_timestamps() -> None:
    with pytest.raises(ValueError, match="last_modified_at_ms"):
        RowLineage(
            table="users",
            pk="1",
            created_at_ms=2_000_000,
            last_modified_at_ms=1_000_000,
            n_updates=0,
            is_deleted=False,
        )


def test_row_lineage_rejects_negative() -> None:
    with pytest.raises(ValueError):
        RowLineage(
            table="users",
            pk="1",
            created_at_ms=1_000,
            last_modified_at_ms=2_000,
            n_updates=-1,
            is_deleted=False,
        )
