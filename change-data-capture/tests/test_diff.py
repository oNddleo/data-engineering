"""Column-level diff: change_vector + columns_changed + is_no_op_update."""

from __future__ import annotations

import pytest

from cdc.diff import change_vector, columns_changed, is_no_op_update
from cdc.schema import CDCEvent, Op

from ._fixtures import make_insert, make_update, pos


def test_change_vector_single_column() -> None:
    cv = change_vector(make_update())
    assert cv.changed_columns == ("age",)
    assert cv.before_values == {"age": 30}
    assert cv.after_values == {"age": 31}


def test_change_vector_multiple_columns() -> None:
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "name": "Alice", "age": 30, "tier": "silver"},
        after={"id": 1, "name": "Alice", "age": 31, "tier": "gold"},
    )
    cv = change_vector(e)
    assert cv.changed_columns == ("age", "tier")


def test_change_vector_no_op() -> None:
    """An UPDATE where nothing actually changed → empty change vector."""
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "name": "Alice", "age": 30},
        after={"id": 1, "name": "Alice", "age": 30},
    )
    cv = change_vector(e)
    assert cv.is_no_op
    assert cv.changed_columns == ()


def test_columns_changed_helper() -> None:
    assert columns_changed(make_update()) == ("age",)


def test_is_no_op_update_true() -> None:
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "x": 100},
        after={"id": 1, "x": 100},
    )
    assert is_no_op_update(e) is True


def test_is_no_op_update_false() -> None:
    assert is_no_op_update(make_update()) is False


def test_change_vector_rejects_non_update() -> None:
    with pytest.raises(ValueError, match="UPDATE"):
        change_vector(make_insert())


def test_columns_changed_rejects_non_update() -> None:
    with pytest.raises(ValueError):
        columns_changed(make_insert())


def test_is_no_op_rejects_non_update() -> None:
    with pytest.raises(ValueError):
        is_no_op_update(make_insert())


def test_change_vector_handles_added_column() -> None:
    """When after has a new key, it counts as a change (before=None)."""
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "name": "Alice"},
        after={"id": 1, "name": "Alice", "extra": "new!"},
    )
    cv = change_vector(e)
    assert "extra" in cv.changed_columns


def test_change_vector_handles_removed_column() -> None:
    """When before has a key removed in after."""
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "name": "Alice", "old": "x"},
        after={"id": 1, "name": "Alice"},
    )
    cv = change_vector(e)
    assert "old" in cv.changed_columns


def test_change_vector_preserves_table_and_pk() -> None:
    cv = change_vector(make_update())
    assert cv.table == "users"
    assert cv.pk == "1"


def test_change_vector_null_to_value() -> None:
    """NULL → value counts as a change."""
    e = CDCEvent(
        op=Op.UPDATE,
        table="users",
        pk="1",
        ts_ms=1_000_000,
        position=pos(offset=1),
        before={"id": 1, "email": None},
        after={"id": 1, "email": "a@b.com"},
    )
    cv = change_vector(e)
    assert cv.changed_columns == ("email",)
    assert cv.before_values["email"] is None
