"""JSON codec round-trips."""

from __future__ import annotations

import pytest

from schemaev.io_json import (
    field_from_dict,
    parse_compatibility,
    report_to_json,
    schema_from_dict,
    schema_from_json,
    schema_to_dict,
    schema_to_json,
)
from schemaev.schema import (
    Compatibility,
    CompatibilityReport,
    FieldType,
)

from ._fixtures import make_field, make_schema


def test_field_roundtrip():
    f = make_field(name="x", type=FieldType.LONG, required=False, default="0", aliases=("old_x",))
    back = field_from_dict(
        {
            "name": "x",
            "type": "LONG",
            "required": False,
            "default": "0",
            "aliases": ["old_x"],
        }
    )
    assert back == f


def test_schema_roundtrip():
    s = make_schema(
        fields=(
            make_field(name="a"),
            make_field(name="b", type=FieldType.BOOL),
        )
    )
    back = schema_from_json(schema_to_json(s))
    assert back == s


def test_schema_dict_format_stable():
    s = make_schema()
    d = schema_to_dict(s)
    assert d["name"] == "Order"
    assert d["version"] == "1.0.0"
    assert isinstance(d["fields"], list)


def test_field_decoder_rejects_unknown_type():
    bad = {"name": "x", "type": "DECIMAL", "required": True, "default": None, "aliases": []}
    with pytest.raises(ValueError):
        field_from_dict(bad)


def test_schema_decoder_rejects_non_object():
    with pytest.raises(TypeError):
        schema_from_json("[]")


def test_schema_decoder_rejects_non_list_fields():
    with pytest.raises(TypeError, match="fields"):
        schema_from_dict({"name": "X", "version": "1.0.0", "fields": "not a list"})


def test_parse_compatibility_case_insensitive():
    assert parse_compatibility("backward") is Compatibility.BACKWARD
    assert parse_compatibility("FORWARD") is Compatibility.FORWARD
    assert parse_compatibility("Full") is Compatibility.FULL


def test_parse_compatibility_rejects_unknown():
    with pytest.raises(ValueError):
        parse_compatibility("RELATIVE")


def test_report_to_json_round_trips_basic_shape():
    r = CompatibilityReport(
        mode=Compatibility.BACKWARD,
        is_compatible=False,
        breaking_changes=(),
        safe_changes=(),
    )
    text = report_to_json(r)
    import json

    parsed = json.loads(text)
    assert parsed["mode"] == "BACKWARD"
    assert parsed["is_compatible"] is False
