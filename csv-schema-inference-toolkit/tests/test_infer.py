"""Type-inference engine — end-to-end per-column tests."""

from __future__ import annotations

from csvinf.infer import infer_schema
from csvinf.schema import ColumnType


def test_infer_all_int():
    text = "qty\n1\n2\n3\n"
    s = infer_schema(text)
    assert s.column("qty").type is ColumnType.INT
    assert s.column("qty").min_value == "1"
    assert s.column("qty").max_value == "3"


def test_infer_all_float():
    text = "ratio\n0.5\n1.5\n2.75\n"
    s = infer_schema(text)
    assert s.column("ratio").type is ColumnType.FLOAT


def test_infer_int_with_vn_thousands():
    text = "amount\n1.234.567\n12.345\n100\n"
    s = infer_schema(text)
    assert s.column("amount").type is ColumnType.INT


def test_infer_decimal_vn():
    """Quote values so VN decimals (with commas) don't collide with the comma delimiter."""
    text = "amount\n" '"1.500.000,00"\n' '"2.300.000,50"\n' '"50,75"\n'
    s = infer_schema(text)
    assert s.column("amount").type is ColumnType.DECIMAL


def test_infer_bool_yes_no():
    text = "paid\ntrue\nfalse\ntrue\nyes\nno\n"
    s = infer_schema(text)
    assert s.column("paid").type is ColumnType.BOOL


def test_infer_bool_vn_co_khong():
    text = "paid\nCó\nKhông\nCó\nKhông\n"
    s = infer_schema(text)
    assert s.column("paid").type is ColumnType.BOOL


def test_infer_date_vn():
    text = "dob\n17/05/2026\n01/01/2025\n31/12/2024\n"
    s = infer_schema(text)
    col = s.column("dob")
    assert col.type is ColumnType.DATE
    assert col.detected_format == "dd/MM/yyyy"
    assert col.min_value == "2024-12-31"
    assert col.max_value == "2026-05-17"


def test_infer_date_iso():
    text = "dob\n2024-12-31\n2025-01-01\n2026-05-17\n"
    s = infer_schema(text)
    col = s.column("dob")
    assert col.type is ColumnType.DATE
    assert col.detected_format == "yyyy-mm-dd"


def test_infer_datetime():
    text = "ts\n2026-05-17T09:00:00\n2026-05-18T10:30:00\n"
    s = infer_schema(text)
    assert s.column("ts").type is ColumnType.DATETIME


def test_infer_string_when_mixed():
    """If any cell fails, we fall through to STRING."""
    text = "kind\nhello\n42\nworld\n"
    s = infer_schema(text)
    assert s.column("kind").type is ColumnType.STRING


def test_infer_nullable_when_empty_present():
    text = "name\nAlice\n\nBob\n"
    s = infer_schema(text)
    col = s.column("name")
    assert col.nullable is True
    assert col.n_non_null == 2
    assert col.n_rows == 3


def test_infer_cardinality_capped():
    """Cardinality returns MAX_CARDINALITY+1 when there are many distinct values."""
    from csvinf.schema import MAX_CARDINALITY

    rows = "\n".join(str(i) for i in range(MAX_CARDINALITY + 50))
    text = f"id\n{rows}\n"
    s = infer_schema(text)
    col = s.column("id")
    assert col.cardinality == MAX_CARDINALITY + 1
    assert col.is_high_cardinality is True


def test_infer_examples_first_five():
    text = "fruit\napple\nbanana\ncherry\ndate\nelder\nfig\n"
    s = infer_schema(text)
    assert s.column("fruit").examples == ("apple", "banana", "cherry", "date", "elder")


def test_infer_with_synthetic_full_csv():
    """End-to-end inference on the simulator output."""
    from csvinf.simulator import generate

    csv_text = generate(n_rows=50, seed=7)
    s = infer_schema(csv_text, source_name="orders.csv")
    assert s.has_header
    assert s.n_rows_scanned == 50
    types = {c.name: c.type for c in s.columns}
    assert types["order_id"] is ColumnType.INT
    assert types["amount_vnd"] is ColumnType.DECIMAL
    assert types["is_paid"] is ColumnType.BOOL
    assert types["created_date"] is ColumnType.DATE
    assert types["signed_at"] is ColumnType.DATETIME
    assert types["email"] is ColumnType.STRING


def test_infer_empty_csv():
    s = infer_schema("")
    assert s.columns == ()
    assert s.n_rows_scanned == 0
