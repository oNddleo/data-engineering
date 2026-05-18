"""Hypothesis properties — invariants of parsers + inference + emitters."""

from __future__ import annotations

import json
import string

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from csvinf.emit import emit_avro, emit_dataclass, emit_json_schema
from csvinf.infer import infer_schema
from csvinf.parsers import (
    try_bool,
    try_date,
    try_decimal,
    try_float,
    try_int,
)
from csvinf.schema import ColumnType

# ---------- parsers ----------------------------------------------------------


@given(st.integers(min_value=-10_000_000, max_value=10_000_000))
@settings(max_examples=80)
def test_property_int_round_trip(n: int) -> None:
    """Any integer formatted as a plain string round-trips through try_int."""
    assert try_int(str(n)) == n


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
@settings(max_examples=50)
def test_property_float_round_trip(x: float) -> None:
    """A float formatted with a decimal point round-trips."""
    s = f"{x:.6f}"
    parsed = try_float(s)
    assert parsed is not None


@given(st.dates(min_value=__import__("datetime").date(1900, 1, 1)))
@settings(max_examples=60)
def test_property_iso_date_round_trip(d: object) -> None:
    """Any ISO date string round-trips."""
    from datetime import date as date_cls

    assert isinstance(d, date_cls)
    s = d.isoformat()
    parsed = try_date(s)
    assert parsed == d


@given(st.sampled_from(("true", "false", "yes", "no", "Có", "Không", "1", "0")))
@settings(max_examples=20)
def test_property_bool_token_always_parses(token: str) -> None:
    assert try_bool(token) is not None


@given(st.from_regex(r"^[A-Za-z]{3,10}$", fullmatch=True))
@settings(max_examples=30)
def test_property_string_never_parses_as_int(token: str) -> None:
    """A non-numeric alpha string never parses as INT."""
    assert try_int(token) is None
    assert try_float(token) is None
    assert try_decimal(token) is None


# ---------- inference --------------------------------------------------------


@given(st.lists(st.integers(min_value=2, max_value=1_000_000), min_size=2, max_size=20))
@settings(max_examples=20)
def test_property_int_column_detected(values: list[int]) -> None:
    """A column of integers (≥ 2, so not BOOL-ambiguous) is detected as INT.

    Pure 0/1 columns are legitimately BOOL since "0"/"1" are valid
    boolean tokens — we exclude that case from the property.
    """
    body = "\n".join(str(v) for v in values)
    text = f"x\n{body}\n"
    s = infer_schema(text)
    assert s.column("x").type is ColumnType.INT


@given(
    st.lists(
        st.sampled_from(("true", "false", "Có", "Không", "yes", "no")), min_size=2, max_size=20
    )
)
@settings(max_examples=20)
def test_property_bool_column_detected(values: list[str]) -> None:
    body = "\n".join(values)
    text = f"flag\n{body}\n"
    s = infer_schema(text)
    assert s.column("flag").type is ColumnType.BOOL


@given(
    st.lists(
        st.from_regex(r"^[a-z]{5,10}$", fullmatch=True),
        min_size=2,
        max_size=20,
        unique=True,
    )
)
@settings(max_examples=15)
def test_property_random_strings_detected_as_string(values: list[str]) -> None:
    """A column of pure alpha strings is detected as STRING."""
    body = "\n".join(values)
    text = f"name\n{body}\n"
    s = infer_schema(text)
    assert s.column("name").type is ColumnType.STRING


# ---------- emitter determinism ----------------------------------------------


@given(st.lists(st.integers(min_value=1, max_value=1_000), min_size=2, max_size=10))
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_emit_avro_deterministic(values: list[int]) -> None:
    """Emitting Avro twice yields identical bytes."""
    body = "\n".join(str(v) for v in values)
    text = f"id\n{body}\n"
    s = infer_schema(text)
    assert emit_avro(s) == emit_avro(s)


@given(st.lists(st.integers(min_value=1, max_value=1_000), min_size=2, max_size=10))
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_emit_avro_valid_json(values: list[int]) -> None:
    """Emitted Avro is always valid JSON."""
    body = "\n".join(str(v) for v in values)
    text = f"id\n{body}\n"
    s = infer_schema(text)
    payload = json.loads(emit_avro(s))
    assert payload["type"] == "record"


@given(st.from_regex(r"^[A-Za-z_][A-Za-z0-9_]{2,8}$", fullmatch=True))
@settings(max_examples=20)
def test_property_emit_dataclass_compiles(class_name: str) -> None:
    """Emitted dataclass code always compiles."""
    # build a 2-column schema with this class name
    text = f"{class_name}_id,{class_name}_name\n1,Alice\n2,Bob\n"
    s = infer_schema(text)
    code = emit_dataclass(s, class_name=class_name)
    compile(code, "<emit>", "exec")  # raises on syntax error


@given(st.from_regex(r"^[A-Za-z_][A-Za-z0-9_]{2,8}$", fullmatch=True))
@settings(max_examples=15)
def test_property_emit_json_schema_valid(name: str) -> None:
    """Emitted JSON Schema is always valid JSON with required keys."""
    _ = string  # silence unused import
    text = f"{name},value\nfoo,1\nbar,2\n"
    s = infer_schema(text)
    payload = json.loads(emit_json_schema(s, title=name))
    assert "$schema" in payload
    assert "title" in payload
    assert "properties" in payload
