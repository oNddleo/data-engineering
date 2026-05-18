"""InferredColumn / InferredSchema validation + property helpers."""

from __future__ import annotations

import pytest

from csvinf.schema import (
    MAX_CARDINALITY,
    ColumnType,
    InferredColumn,
    InferredSchema,
)


def _column(**overrides: object) -> InferredColumn:
    defaults: dict[str, object] = {
        "name": "col",
        "type": ColumnType.STRING,
        "nullable": False,
        "n_rows": 10,
        "n_non_null": 10,
        "cardinality": 10,
        "examples": ("a", "b", "c"),
    }
    defaults.update(overrides)
    return InferredColumn(**defaults)  # type: ignore[arg-type]


def test_column_basic_ok():
    c = _column()
    assert c.null_fraction == 0.0
    assert c.is_high_cardinality is False


def test_column_null_fraction_computed():
    c = _column(n_rows=10, n_non_null=7)
    assert c.null_fraction == 0.3


def test_column_zero_rows_zero_null_fraction():
    c = _column(n_rows=0, n_non_null=0, cardinality=0, examples=())
    assert c.null_fraction == 0.0


def test_column_rejects_n_non_null_gt_n_rows():
    with pytest.raises(ValueError, match="n_non_null cannot exceed"):
        _column(n_rows=5, n_non_null=10)


def test_column_rejects_negative_rows():
    with pytest.raises(ValueError, match="n_rows must be >= 0"):
        _column(n_rows=-1)


def test_column_rejects_empty_name():
    with pytest.raises(ValueError, match="name must be non-empty"):
        _column(name="")


def test_column_high_cardinality_when_capped():
    c = _column(cardinality=MAX_CARDINALITY + 1)
    assert c.is_high_cardinality is True


def test_schema_ok():
    s = InferredSchema(
        source_name="orders.csv",
        delimiter=",",
        has_header=True,
        n_rows_scanned=100,
        columns=(_column(name="a"), _column(name="b")),
    )
    assert s.n_rows_scanned == 100


def test_schema_rejects_duplicate_columns():
    with pytest.raises(ValueError, match="duplicate column names"):
        InferredSchema(
            source_name="orders.csv",
            delimiter=",",
            has_header=True,
            n_rows_scanned=10,
            columns=(_column(name="x"), _column(name="x")),
        )


def test_schema_rejects_empty_source():
    with pytest.raises(ValueError, match="source_name"):
        InferredSchema(
            source_name="",
            delimiter=",",
            has_header=True,
            n_rows_scanned=0,
            columns=(),
        )


def test_schema_lookup_column():
    s = InferredSchema(
        source_name="orders.csv",
        delimiter=",",
        has_header=True,
        n_rows_scanned=0,
        columns=(_column(name="a"), _column(name="b")),
    )
    assert s.column("a").name == "a"
    with pytest.raises(KeyError):
        s.column("nope")
