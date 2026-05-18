"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import date

import pytest

from vncal.holidays import build_year
from vncal.io_jsonl import (
    dump_fiscal_years,
    dump_holidays,
    fiscal_year_from_dict,
    fiscal_year_to_dict,
    holiday_from_dict,
    holiday_to_dict,
    load_fiscal_years,
    load_holidays,
)
from vncal.schema import FiscalYear, Holiday, HolidayKind


def test_holiday_round_trip():
    h = Holiday(
        date=date(2026, 5, 1),
        name_vi="Ngày Quốc tế Lao động",
        name_en="International Labour Day",
        kind=HolidayKind.SOLAR_FIXED,
    )
    assert holiday_from_dict(holiday_to_dict(h)) == h


def test_holiday_dump_load_round_trip():
    holidays = build_year(2026)
    loaded = load_holidays(dump_holidays(holidays))
    assert loaded == holidays


def test_holiday_dump_newline_terminated():
    text = dump_holidays(build_year(2026))
    assert text.endswith("\n")


def test_holiday_load_skips_blank_lines():
    h = build_year(2026)[0]
    raw = dump_holidays([h]) + "\n  \n"
    assert load_holidays(raw) == [h]


def test_holiday_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_holidays("[1, 2]\n")


def test_holiday_load_rejects_str_paid():
    """A bool sneaking in as str must be rejected."""
    bad = holiday_to_dict(build_year(2026)[0])
    bad["paid"] = "yes"
    with pytest.raises(TypeError, match="paid must be bool"):
        holiday_from_dict(bad)


def test_fiscal_year_round_trip():
    fy = FiscalYear(
        label="FY2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    assert fiscal_year_from_dict(fiscal_year_to_dict(fy)) == fy
    assert load_fiscal_years(dump_fiscal_years([fy])) == [fy]
