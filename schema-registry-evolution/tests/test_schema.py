"""Schema invariants."""

from __future__ import annotations

import pytest

from schemaev.schema import (
    Compatibility,
    Field,
    FieldChange,
    FieldType,
    Schema,
)

from ._fixtures import make_field, make_schema


def test_field_type_seven_values():
    assert {t.value for t in FieldType} == {
        "STRING",
        "INT",
        "LONG",
        "FLOAT",
        "DOUBLE",
        "BOOL",
        "BYTES",
    }


def test_compatibility_four_modes():
    assert {c.value for c in Compatibility} == {
        "NONE",
        "BACKWARD",
        "FORWARD",
        "FULL",
    }


def test_field_rejects_empty_name():
    with pytest.raises(ValueError):
        make_field(name="")


def test_field_rejects_special_chars_in_name():
    with pytest.raises(ValueError):
        make_field(name="bad-name")


def test_field_underscores_ok():
    f = make_field(name="customer_id")
    assert f.name == "customer_id"


def test_field_rejects_bad_alias():
    with pytest.raises(ValueError):
        Field(name="x", type=FieldType.STRING, aliases=("bad alias",))


def test_schema_rejects_duplicate_field_names():
    with pytest.raises(ValueError, match="duplicate"):
        Schema(
            name="X",
            version="1.0.0",
            fields=(make_field(name="x"), make_field(name="x")),
        )


def test_schema_rejects_empty_name():
    with pytest.raises(ValueError):
        Schema(name="", version="1.0.0", fields=(make_field(),))


def test_schema_field_named_finds_by_alias():
    s = Schema(
        name="X",
        version="1.0.0",
        fields=(make_field(name="buyer_id", aliases=("customer_id",)),),
    )
    assert s.field_named("buyer_id") is not None
    assert s.field_named("customer_id") is not None
    assert s.field_named("ghost") is None


def test_field_change_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        FieldChange(kind="WEIRD", field_name="x", old=None, new=None)


def test_field_change_rejects_empty_field_name():
    with pytest.raises(ValueError):
        FieldChange(kind="ADDED", field_name="", old=None, new=None)


def test_default_schema_passes_validation():
    s = make_schema()
    assert s.name == "Order"
    assert len(s.fields) == 2
