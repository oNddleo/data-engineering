"""Schema diff behaviour."""

from __future__ import annotations

from schemaev.diff import diff
from schemaev.schema import FieldType

from ._fixtures import make_field, make_schema


def test_no_changes_empty_diff():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(fields=(make_field(name="x"),))
    assert diff(old, new) == []


def test_added_field_detected():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    changes = diff(old, new)
    assert len(changes) == 1
    assert changes[0].kind == "ADDED"
    assert changes[0].field_name == "y"


def test_removed_field_detected():
    old = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    new = make_schema(fields=(make_field(name="x"),))
    changes = diff(old, new)
    assert len(changes) == 1
    assert changes[0].kind == "REMOVED"
    assert changes[0].field_name == "y"


def test_type_change_detected():
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    [change] = diff(old, new)
    assert change.kind == "TYPE_CHANGED"
    assert "INT" in change.detail
    assert "LONG" in change.detail


def test_required_change_detected():
    old = make_schema(fields=(make_field(name="x", required=True),))
    new = make_schema(fields=(make_field(name="x", required=False, default=""),))
    changes = diff(old, new)
    # Could fire REQUIRED_CHANGED and DEFAULT_CHANGED both.
    kinds = {c.kind for c in changes}
    assert "REQUIRED_CHANGED" in kinds


def test_default_change_detected():
    old = make_schema(fields=(make_field(name="x", required=False, default="a"),))
    new = make_schema(fields=(make_field(name="x", required=False, default="b"),))
    [change] = diff(old, new)
    assert change.kind == "DEFAULT_CHANGED"


def test_rename_via_alias_not_treated_as_remove_add():
    """A field with old name as an alias on the new field is a rename, not two changes."""
    old = make_schema(fields=(make_field(name="customer_id"),))
    new = make_schema(fields=(make_field(name="buyer_id", aliases=("customer_id",)),))
    changes = diff(old, new)
    kinds = {c.kind for c in changes}
    assert "ADDED" not in kinds
    assert "REMOVED" not in kinds
    assert "ALIAS_ADDED" in kinds


def test_alias_added_to_same_named_field():
    """Adding an alias to an existing field is one change."""
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(fields=(make_field(name="x", aliases=("old_x",)),))
    [change] = diff(old, new)
    assert change.kind == "ALIAS_ADDED"


def test_diff_output_sorted_by_kind_then_name():
    old = make_schema(
        fields=(
            make_field(name="b"),
            make_field(name="c"),
        )
    )
    new = make_schema(
        fields=(
            make_field(name="a"),  # ADDED
            make_field(name="b"),  # unchanged
            make_field(name="d"),  # ADDED
        )
    )
    changes = diff(old, new)
    pairs = [(c.kind, c.field_name) for c in changes]
    assert pairs == sorted(pairs)


def test_diff_multi_change():
    """A combined add + remove + type change emits all three."""
    old = make_schema(
        fields=(
            make_field(name="x", type=FieldType.INT),
            make_field(name="to_remove"),
        )
    )
    new = make_schema(
        fields=(
            make_field(name="x", type=FieldType.LONG),
            make_field(name="to_add"),
        )
    )
    changes = diff(old, new)
    kinds = {c.kind for c in changes}
    assert kinds == {"ADDED", "REMOVED", "TYPE_CHANGED"}
