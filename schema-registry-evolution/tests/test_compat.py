"""Compatibility checker behaviour."""

from __future__ import annotations

from schemaev.compat import check, check_backward, check_forward, check_full
from schemaev.schema import Compatibility, FieldType

from ._fixtures import make_field, make_schema

# ---------- BACKWARD ------------------------------------------------------


def test_backward_add_with_default_compatible():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(
        fields=(
            make_field(name="x"),
            make_field(name="y", required=False, default=""),
        )
    )
    r = check_backward(old, new)
    assert r.is_compatible is True


def test_backward_add_required_no_default_incompatible():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(
        fields=(
            make_field(name="x"),
            make_field(name="y"),  # required=True, no default
        )
    )
    r = check_backward(old, new)
    assert r.is_compatible is False
    assert len(r.breaking_changes) == 1
    assert r.breaking_changes[0].kind == "ADDED"


def test_backward_remove_required_compatible_for_backward():
    """Removing a field is BACKWARD-safe — new schema just ignores extra data."""
    old = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    new = make_schema(fields=(make_field(name="x"),))
    r = check_backward(old, new)
    assert r.is_compatible is True


def test_backward_type_widen_compatible():
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    r = check_backward(old, new)
    assert r.is_compatible is True


def test_backward_type_narrow_incompatible():
    old = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    r = check_backward(old, new)
    assert r.is_compatible is False


def test_backward_string_to_bytes_compatible():
    """String ↔ bytes is bidirectionally safe per Avro spec."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.STRING),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.BYTES),))
    r = check_backward(old, new)
    assert r.is_compatible is True


def test_backward_string_to_int_incompatible():
    old = make_schema(fields=(make_field(name="x", type=FieldType.STRING),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    r = check_backward(old, new)
    assert r.is_compatible is False


def test_backward_optional_to_required_incompatible():
    """Old data may be missing the field; new schema now requires it."""
    old = make_schema(fields=(make_field(name="x", required=False, default=""),))
    new = make_schema(fields=(make_field(name="x", required=True),))
    r = check_backward(old, new)
    assert r.is_compatible is False


def test_backward_required_to_optional_compatible():
    """Loosening required → optional is fine for the reader."""
    old = make_schema(fields=(make_field(name="x", required=True),))
    new = make_schema(fields=(make_field(name="x", required=False, default=""),))
    r = check_backward(old, new)
    assert r.is_compatible is True


def test_backward_rename_with_alias_compatible():
    old = make_schema(fields=(make_field(name="customer_id"),))
    new = make_schema(fields=(make_field(name="buyer_id", aliases=("customer_id",)),))
    r = check_backward(old, new)
    assert r.is_compatible is True


# ---------- FORWARD -------------------------------------------------------


def test_forward_add_field_compatible():
    """Old schema ignores fields it doesn't know about — safe."""
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    r = check_forward(old, new)
    assert r.is_compatible is True


def test_forward_remove_required_no_default_incompatible():
    """Old schema requires the field; new data won't have it."""
    old = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    new = make_schema(fields=(make_field(name="x"),))
    r = check_forward(old, new)
    assert r.is_compatible is False


def test_forward_remove_optional_compatible():
    """Old schema had it as optional → fine if it's missing in new data."""
    old = make_schema(
        fields=(
            make_field(name="x"),
            make_field(name="y", required=False, default=""),
        )
    )
    new = make_schema(fields=(make_field(name="x"),))
    r = check_forward(old, new)
    assert r.is_compatible is True


def test_forward_type_narrow_compatible():
    """For FORWARD compat, narrowing is safe: old reader reads as wider type."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    r = check_forward(old, new)
    assert r.is_compatible is True


def test_forward_type_widen_incompatible():
    """Widening is FORWARD-unsafe — old reader can't hold the bigger values."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    r = check_forward(old, new)
    assert r.is_compatible is False


# ---------- FULL ----------------------------------------------------------


def test_full_requires_both_directions():
    """A widen is BACKWARD-safe but not FORWARD-safe — FAILS FULL."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    r = check_full(old, new)
    assert r.is_compatible is False


def test_full_add_optional_compatible():
    """Adding optional with default is safe in both directions."""
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(
        fields=(
            make_field(name="x"),
            make_field(name="y", required=False, default=""),
        )
    )
    r = check_full(old, new)
    assert r.is_compatible is True


def test_full_remove_required_incompatible():
    """Removing required breaks FORWARD even though BACKWARD is fine."""
    old = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    new = make_schema(fields=(make_field(name="x"),))
    r = check_full(old, new)
    assert r.is_compatible is False


# ---------- NONE / dispatch ----------------------------------------------


def test_none_always_compatible():
    """NONE skips all checks — always returns compatible."""
    old = make_schema(fields=(make_field(name="x"),))
    # Totally different schema — still compatible under NONE.
    new = make_schema(fields=(make_field(name="completely_different"),))
    r = check(old, new, Compatibility.NONE)
    assert r.is_compatible is True


def test_check_dispatches_to_correct_mode():
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    assert check(old, new, Compatibility.BACKWARD).is_compatible is True
    assert check(old, new, Compatibility.FORWARD).is_compatible is False
    assert check(old, new, Compatibility.FULL).is_compatible is False
