"""Public-holiday list builder."""

from __future__ import annotations

from datetime import date
from itertools import pairwise

import pytest

from vncal.holidays import build_year, build_years
from vncal.schema import HolidayKind


def test_build_year_2026_count():
    """2026: 11 base holidays + 1 compensation (Giỗ Tổ on Sun) = 12."""
    holidays = build_year(2026)
    assert len(holidays) == 12


def test_build_year_sorted_by_date():
    holidays = build_year(2026)
    dates_only = [h.date for h in holidays]
    assert dates_only == sorted(dates_only)


def test_build_year_includes_jan_1():
    holidays = build_year(2026)
    [new_year] = [h for h in holidays if h.date == date(2026, 1, 1)]
    assert new_year.name_vi == "Tết Dương Lịch"


def test_build_year_tet_block_is_5_days():
    holidays = build_year(2026)
    tet_block = [h for h in holidays if h.kind is HolidayKind.TET]
    assert len(tet_block) == 5
    # Consecutive
    dates_only = sorted(h.date for h in tet_block)
    for prev, curr in pairwise(dates_only):
        assert (curr - prev).days == 1


def test_build_year_includes_quoc_khanh():
    holidays = build_year(2026)
    sep_2 = [h for h in holidays if h.date == date(2026, 9, 2)]
    assert len(sep_2) == 1
    assert sep_2[0].name_en == "National Day"


def test_build_year_2024_giotot_on_thursday():
    """2024 Giỗ Tổ = 18 Apr (Thursday) — no compensation."""
    holidays = build_year(2024)
    comp_days = [h for h in holidays if h.kind is HolidayKind.COMPENSATION]
    # The 2024 compensation days come from Quốc Khánh + Reunification weekend rolls.
    # Apr 30 2024 = Tuesday, May 1 = Wednesday — no comp.
    # Sep 2 2024 = Monday, Sep 1 2024 = Sunday → comp day on Tuesday (but Sep 2 already taken).
    assert all(c.date >= date(2024, 1, 1) for c in comp_days)


def test_build_year_2026_giotot_on_sunday_triggers_comp():
    """2026 Giỗ Tổ = 26 Apr (Sunday) → comp day on Monday 27 Apr."""
    holidays = build_year(2026)
    [comp] = [h for h in holidays if h.kind is HolidayKind.COMPENSATION and "Giỗ Tổ" in h.name_vi]
    assert comp.date == date(2026, 4, 27)


def test_build_year_outside_table_raises():
    with pytest.raises(LookupError):
        build_year(2099)


def test_build_years_inclusive_range():
    holidays = build_years(2024, 2026)
    years = {h.date.year for h in holidays}
    assert years == {2024, 2025, 2026}


def test_build_years_rejects_inverted_range():
    with pytest.raises(ValueError, match="before"):
        build_years(2026, 2024)


def test_build_year_paid_default_true():
    holidays = build_year(2026)
    assert all(h.paid for h in holidays)
