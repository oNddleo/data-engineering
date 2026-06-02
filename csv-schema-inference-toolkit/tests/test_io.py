"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from csvinf.io_jsonl import (
    column_from_dict,
    column_to_dict,
    dump_schemas,
    load_schemas,
    schema_from_dict,
    schema_to_dict,
)
from csvinf.schema import ColumnType, InferredColumn, InferredSchema


def _column() -> InferredColumn:
    return InferredColumn(
        name="amount",
        type=ColumnType.DECIMAL,
        nullable=False,
        n_rows=100,
        n_non_null=100,
        cardinality=85,
        examples=("100.50", "200.75"),
        min_value="0.00",
        max_value="999999.99",
        detected_format="",
    )


def _schema() -> InferredSchema:
    return InferredSchema(
        source_name="orders.csv",
        delimiter=",",
        has_header=True,
        n_rows_scanned=100,
        columns=(_column(),),
    )


def test_column_round_trip():
    c = _column()
    assert column_from_dict(column_to_dict(c)) == c


def test_schema_round_trip():
    s = _schema()
    assert schema_from_dict(schema_to_dict(s)) == s


def test_dump_load_round_trip():
    schemas = [_schema()]
    assert load_schemas(dump_schemas(schemas)) == schemas


def test_dump_emits_newline_terminated():
    text = dump_schemas([_schema()])
    assert text.endswith("\n")
    assert text.count("\n") == 1


def test_load_skips_blank_lines():
    raw = dump_schemas([_schema()]) + "\n   \n"
    assert load_schemas(raw) == [_schema()]


def test_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_schemas("[1, 2]\n")


def test_column_load_rejects_bool_int():
    """A bool sneaking in as int must be rejected."""
    bad = column_to_dict(_column())
    bad["n_rows"] = True
    with pytest.raises(TypeError, match="n_rows must be int"):
        column_from_dict(bad)


def test_column_load_rejects_non_bool_nullable():
    bad = column_to_dict(_column())
    bad["nullable"] = "yes"
    with pytest.raises(TypeError, match="nullable must be bool"):
        column_from_dict(bad)


def test_schema_load_rejects_non_list_columns():
    bad = schema_to_dict(_schema())
    bad["columns"] = "not a list"
    with pytest.raises(TypeError, match="columns must be list"):
        schema_from_dict(bad)


def test_schema_load_rejects_non_dict_column():
    bad = schema_to_dict(_schema())
    bad["columns"] = [42]
    with pytest.raises(TypeError, match="column must be dict"):
        schema_from_dict(bad)
