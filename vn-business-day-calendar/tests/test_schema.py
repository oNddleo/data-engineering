"""Holiday + FiscalYear validation."""

from __future__ import annotations

from datetime import date

import pytest

from vncal.schema import FiscalYear, Holiday, HolidayKind


def test_holiday_basic():
    h = Holiday(
        date=date(2026, 1, 1),
        name_vi="Tết Dương Lịch",
        name_en="New Year's Day",
        kind=HolidayKind.SOLAR_FIXED,
    )
    assert h.paid is True


def test_holiday_rejects_empty_vi():
    with pytest.raises(ValueError, match="name_vi"):
        Holiday(
            date=date(2026, 1, 1),
            name_vi="",
            name_en="X",
            kind=HolidayKind.SOLAR_FIXED,
        )


def test_holiday_rejects_empty_en():
    with pytest.raises(ValueError, match="name_en"):
        Holiday(
            date=date(2026, 1, 1),
            name_vi="X",
            name_en="",
            kind=HolidayKind.SOLAR_FIXED,
        )


def test_holiday_kinds_complete():
    """Six kinds covered."""
    assert {k.value for k in HolidayKind} == {
        "SOLAR_FIXED",
        "LUNAR_FIXED",
        "TET",
        "COMPENSATION",
        "OPTIONAL",
        "BRIDGE",
    }


def test_fiscal_year_contains():
    fy = FiscalYear(
        label="FY2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    assert fy.contains(date(2026, 5, 18)) is True
    assert fy.contains(date(2025, 12, 31)) is False
    assert fy.contains(date(2027, 1, 1)) is False
    # Inclusive both ends.
    assert fy.contains(date(2026, 1, 1)) is True
    assert fy.contains(date(2026, 12, 31)) is True


def test_fiscal_year_days_in_year_365():
    fy = FiscalYear(
        label="FY2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    assert fy.days_in_year() == 365


def test_fiscal_year_days_in_year_leap_366():
    fy = FiscalYear(
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    assert fy.days_in_year() == 366


def test_fiscal_year_rejects_end_before_start():
    with pytest.raises(ValueError, match="before start_date"):
        FiscalYear(
            label="bad",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )


def test_fiscal_year_rejects_empty_label():
    with pytest.raises(ValueError, match="label"):
        FiscalYear(
            label="",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
