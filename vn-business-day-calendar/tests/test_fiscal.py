"""Fiscal-year helpers."""

from __future__ import annotations

from datetime import date

from vncal.fiscal import april_march_fy, calendar_fy, fiscal_year_for


def test_calendar_fy_basic():
    fy = calendar_fy(2026)
    assert fy.label == "FY2026"
    assert fy.start_date == date(2026, 1, 1)
    assert fy.end_date == date(2026, 12, 31)


def test_april_march_fy_basic():
    fy = april_march_fy(2026)
    assert fy.label == "FY2025-26"
    assert fy.start_date == date(2025, 4, 1)
    assert fy.end_date == date(2026, 3, 31)


def test_fiscal_year_for_calendar_mid_year():
    fy = fiscal_year_for(date(2026, 5, 18))
    assert fy.label == "FY2026"


def test_fiscal_year_for_calendar_year_end():
    fy = fiscal_year_for(date(2026, 12, 31))
    assert fy.label == "FY2026"


def test_fiscal_year_for_april_march_before_apr():
    """1 Mar 2026 is in FY2025-26."""
    fy = fiscal_year_for(date(2026, 3, 31), april_march=True)
    assert fy.label == "FY2025-26"


def test_fiscal_year_for_april_march_after_apr():
    """1 Apr 2026 is in FY2026-27."""
    fy = fiscal_year_for(date(2026, 4, 1), april_march=True)
    assert fy.label == "FY2026-27"


def test_calendar_fy_leap_year_366_days():
    assert calendar_fy(2024).days_in_year() == 366


def test_april_march_fy_365_days():
    """Apr 2024 → Mar 2025: contains no Feb 29 → 365 days.

    Wait — Apr 1 2024 to Mar 31 2025 — only Feb 2025 is in window (28 days). 365 days.
    """
    assert april_march_fy(2025).days_in_year() == 365
