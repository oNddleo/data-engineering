"""Per-type parser tests covering VN locale edge cases."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from csvinf.parsers import (
    detect_date_format,
    detect_datetime_format,
    try_bool,
    try_date,
    try_datetime,
    try_decimal,
    try_float,
    try_int,
)

# ---------- bool -------------------------------------------------------------


def test_bool_true_tokens():
    for v in ("true", "TRUE", "yes", "Y", "1", "Có", "có", "Co"):
        assert try_bool(v) is True


def test_bool_false_tokens():
    for v in ("false", "no", "N", "0", "Không", "khong"):
        assert try_bool(v) is False


def test_bool_rejects_other():
    for v in ("maybe", "2", "", "  ", "yes!"):
        assert try_bool(v) is None


# ---------- int --------------------------------------------------------------


def test_int_plain():
    assert try_int("0") == 0
    assert try_int("123") == 123
    assert try_int("-99") == -99


def test_int_vn_thousands():
    assert try_int("1.234.567") == 1_234_567
    assert try_int("12.345") == 12_345


def test_int_en_thousands():
    assert try_int("1,234,567") == 1_234_567


def test_int_rejects_float():
    assert try_int("1.5") is None
    assert try_int("1,5") is None


def test_int_rejects_alpha():
    assert try_int("abc") is None
    assert try_int("12abc") is None


def test_int_rejects_empty():
    assert try_int("") is None


# ---------- float ------------------------------------------------------------


def test_float_simple():
    assert try_float("1.5") == 1.5
    assert try_float("-2.75") == -2.75


def test_float_scientific():
    assert try_float("1.5e-3") == 1.5e-3


def test_float_rejects_int():
    """An integer-looking string is NOT a float."""
    assert try_float("42") is None


def test_float_rejects_vn_decimal():
    """VN-locale decimals go through try_decimal, not try_float."""
    assert try_float("1.234,56") is None


# ---------- decimal ----------------------------------------------------------


def test_decimal_vn_thousands_and_comma():
    assert try_decimal("1.234.567,89") == "1234567.89"


def test_decimal_simple_comma():
    assert try_decimal("123,45") == "123.45"


def test_decimal_rejects_period_decimal():
    """A period-decimal (EN locale) is NOT a VN decimal."""
    assert try_decimal("1.5") is None


def test_decimal_negative():
    assert try_decimal("-1.234,56") == "-1234.56"


# ---------- date -------------------------------------------------------------


def test_date_iso():
    assert try_date("2026-05-17") == date(2026, 5, 17)


def test_date_vn():
    assert try_date("17/05/2026") == date(2026, 5, 17)
    assert try_date("17-05-2026") == date(2026, 5, 17)


def test_date_rejects_out_of_range():
    assert try_date("32/05/2026") is None
    assert try_date("17/13/2026") is None
    assert try_date("2026-02-30") is None


def test_date_rejects_random():
    assert try_date("hello") is None
    assert try_date("") is None


def test_detect_date_format_vn():
    assert detect_date_format("17/05/2026") == "dd/MM/yyyy"


def test_detect_date_format_iso():
    assert detect_date_format("2026-05-17") == "yyyy-mm-dd"


def test_detect_date_format_unknown():
    assert detect_date_format("hello") == ""


# ---------- datetime ---------------------------------------------------------


def test_datetime_iso():
    out = try_datetime("2026-05-17T09:00:00")
    assert out == datetime(2026, 5, 17, 9, 0, 0)


def test_datetime_with_timezone():
    out = try_datetime("2026-05-17T09:00:00+07:00")
    assert out is not None
    assert out.tzinfo is not None


def test_datetime_zulu():
    out = try_datetime("2026-05-17T09:00:00Z")
    assert out is not None
    assert out.tzinfo == timezone.utc or out.utcoffset() == timedelta(0)


def test_datetime_rejects_date_only():
    """A pure date is NOT a datetime."""
    assert try_datetime("2026-05-17") is None


def test_datetime_rejects_random():
    assert try_datetime("not a datetime") is None


def test_detect_datetime_format_iso():
    assert detect_datetime_format("2026-05-17T09:00:00") == "iso8601"


def test_detect_datetime_format_unknown():
    assert detect_datetime_format("hello") == ""
