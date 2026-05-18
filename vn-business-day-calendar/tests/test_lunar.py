"""Lunar→solar table coverage and known-value spot checks."""

from __future__ import annotations

from datetime import date

import pytest

from vncal.lunar import (
    gio_to_solar,
    max_year,
    min_year,
    supported_years,
    tet_solar,
)


def test_supported_range():
    """Table covers at least 2020-2035."""
    assert min_year() <= 2020
    assert max_year() >= 2035


def test_tet_2024():
    """2024 Tết = 10 Feb (Year of the Dragon)."""
    assert tet_solar(2024) == date(2024, 2, 10)


def test_tet_2025():
    """2025 Tết = 29 Jan (Year of the Snake)."""
    assert tet_solar(2025) == date(2025, 1, 29)


def test_tet_2026():
    """2026 Tết = 17 Feb (Year of the Horse)."""
    assert tet_solar(2026) == date(2026, 2, 17)


def test_tet_2020():
    """2020 Tết = 25 Jan (Year of the Rat)."""
    assert tet_solar(2020) == date(2020, 1, 25)


def test_gio_to_2024():
    """Giỗ Tổ 2024 = 18 Apr."""
    assert gio_to_solar(2024) == date(2024, 4, 18)


def test_gio_to_2026():
    """Giỗ Tổ 2026 = 26 Apr."""
    assert gio_to_solar(2026) == date(2026, 4, 26)


def test_tet_unsupported_year_raises():
    with pytest.raises(LookupError, match="not bundled"):
        tet_solar(1999)
    with pytest.raises(LookupError, match="not bundled"):
        tet_solar(2099)


def test_gio_to_unsupported_year_raises():
    with pytest.raises(LookupError, match="not bundled"):
        gio_to_solar(1999)


def test_supported_years_sorted():
    years = supported_years()
    assert years == tuple(sorted(years))


def test_supported_years_complete():
    """Every year in [min_year, max_year] is bundled."""
    years = set(supported_years())
    for y in range(min_year(), max_year() + 1):
        assert y in years
