"""Emit Avro / JSON Schema / dataclass."""

from __future__ import annotations

import json

from csvinf.emit import emit_avro, emit_dataclass, emit_json_schema
from csvinf.infer import infer_schema
from csvinf.schema import ColumnType, InferredColumn, InferredSchema


def _toy_schema() -> InferredSchema:
    return InferredSchema(
        source_name="orders.csv",
        delimiter=",",
        has_header=True,
        n_rows_scanned=10,
        columns=(
            InferredColumn(
                name="order_id",
                type=ColumnType.INT,
                nullable=False,
                n_rows=10,
                n_non_null=10,
                cardinality=10,
                examples=("1", "2"),
            ),
            InferredColumn(
                name="customer",
                type=ColumnType.STRING,
                nullable=True,
                n_rows=10,
                n_non_null=8,
                cardinality=8,
                examples=("Alice", "Bob"),
            ),
            InferredColumn(
                name="amount",
                type=ColumnType.DECIMAL,
                nullable=False,
                n_rows=10,
                n_non_null=10,
                cardinality=10,
                examples=("100.50",),
            ),
            InferredColumn(
                name="created",
                type=ColumnType.DATE,
                nullable=False,
                n_rows=10,
                n_non_null=10,
                cardinality=10,
                examples=("2026-05-17",),
                detected_format="yyyy-mm-dd",
            ),
        ),
    )


# ---------- avro --------------------------------------------------------------


def test_avro_basic():
    payload = json.loads(emit_avro(_toy_schema(), record_name="Order"))
    assert payload["type"] == "record"
    assert payload["name"] == "Order"
    assert len(payload["fields"]) == 4


def test_avro_nullable_union():
    payload = json.loads(emit_avro(_toy_schema()))
    customer = next(f for f in payload["fields"] if f["name"] == "customer")
    assert customer["type"] == ["null", "string"]
    assert customer["default"] is None


def test_avro_required_no_default():
    payload = json.loads(emit_avro(_toy_schema()))
    order_id = next(f for f in payload["fields"] if f["name"] == "order_id")
    assert order_id["type"] == "long"
    assert "default" not in order_id


def test_avro_decimal_logical_type():
    payload = json.loads(emit_avro(_toy_schema()))
    amount = next(f for f in payload["fields"] if f["name"] == "amount")
    assert amount["type"] == {
        "type": "bytes",
        "logicalType": "decimal",
        "precision": 18,
        "scale": 4,
    }


def test_avro_date_logical_type():
    payload = json.loads(emit_avro(_toy_schema()))
    created = next(f for f in payload["fields"] if f["name"] == "created")
    assert created["type"] == {"type": "int", "logicalType": "date"}


def test_avro_deterministic():
    """Emitting twice gives identical output."""
    s = _toy_schema()
    assert emit_avro(s) == emit_avro(s)


# ---------- json schema -------------------------------------------------------


def test_json_schema_basic():
    payload = json.loads(emit_json_schema(_toy_schema(), title="Order"))
    assert payload["title"] == "Order"
    assert payload["type"] == "object"
    assert "order_id" in payload["properties"]
    assert "customer" in payload["properties"]


def test_json_schema_required_list_excludes_nullable():
    payload = json.loads(emit_json_schema(_toy_schema()))
    assert "order_id" in payload["required"]
    assert "amount" in payload["required"]
    assert "customer" not in payload["required"]


def test_json_schema_nullable_type_union():
    payload = json.loads(emit_json_schema(_toy_schema()))
    assert payload["properties"]["customer"]["type"] == ["string", "null"]


def test_json_schema_date_format():
    payload = json.loads(emit_json_schema(_toy_schema()))
    assert payload["properties"]["created"]["format"] == "date"


def test_json_schema_examples_carried():
    payload = json.loads(emit_json_schema(_toy_schema()))
    assert payload["properties"]["order_id"]["examples"] == ["1", "2"]


# ---------- dataclass --------------------------------------------------------


def test_dataclass_basic():
    code = emit_dataclass(_toy_schema(), class_name="Order")
    assert "class Order:" in code
    assert "@dataclass(frozen=True, slots=True)" in code
    assert "order_id: int" in code


def test_dataclass_nullable_optional_with_default():
    code = emit_dataclass(_toy_schema())
    assert "customer: str | None = None" in code


def test_dataclass_required_before_nullable():
    """Required fields come before nullable defaults — Python init order."""
    code = emit_dataclass(_toy_schema())
    idx_required = code.index("order_id: int")
    idx_nullable = code.index("customer: str | None")
    assert idx_required < idx_nullable


def test_dataclass_imports_date():
    code = emit_dataclass(_toy_schema())
    assert "from datetime import date" in code


def test_dataclass_runs():
    """Emitted code is valid Python (exec without raising)."""
    code = emit_dataclass(_toy_schema(), class_name="Order")
    ns: dict[str, object] = {}
    exec(compile(code, "<emit>", "exec"), ns)
    assert "Order" in ns


def test_dataclass_sanitizes_invalid_names():
    """Columns named 'first name' or starting with digit get sanitized."""
    bad_schema = InferredSchema(
        source_name="x.csv",
        delimiter=",",
        has_header=True,
        n_rows_scanned=1,
        columns=(
            InferredColumn(
                name="first name",
                type=ColumnType.STRING,
                nullable=False,
                n_rows=1,
                n_non_null=1,
                cardinality=1,
                examples=("Alice",),
            ),
            InferredColumn(
                name="2nd_field",
                type=ColumnType.INT,
                nullable=False,
                n_rows=1,
                n_non_null=1,
                cardinality=1,
                examples=("1",),
            ),
        ),
    )
    code = emit_dataclass(bad_schema)
    assert "first_name: str" in code
    assert "_2nd_field: int" in code


def test_dataclass_empty_schema_emits_pass():
    """An empty column list emits ``pass``."""
    empty = InferredSchema(
        source_name="x.csv",
        delimiter=",",
        has_header=False,
        n_rows_scanned=0,
        columns=(),
    )
    code = emit_dataclass(empty)
    assert "    pass" in code


# ---------- end-to-end -------------------------------------------------------


def test_emit_avro_round_trip_from_inference():
    """Inference output is valid input to the Avro emitter."""
    text = (
        "order_id,name,amount,paid,dob\n"
        "1,Alice,100.50,true,2026-05-17\n"
        "2,Bob,200.75,false,2026-05-18\n"
    )
    s = infer_schema(text)
    payload = json.loads(emit_avro(s))
    assert payload["type"] == "record"
    assert {f["name"] for f in payload["fields"]} == {
        "order_id",
        "name",
        "amount",
        "paid",
        "dob",
    }
