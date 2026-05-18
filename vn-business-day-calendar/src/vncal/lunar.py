"""Vietnamese lunar calendar — Tết + Giỗ Tổ solar conversions.

Vietnam uses the **Chinese lunar calendar** with one local rule
(astronomical observations adjusted to UTC+7), so VN Tết
occasionally differs by one day from Chinese New Year.

Rather than implement the full astronomical algorithm (sun/moon
longitude computations, the 19-year Metonic cycle, leap-month
insertion rules per the Bureau of Astronomy), we bundle a
**lookup table** of pre-computed dates for 2020-2035. The table
is reviewed against the official VN Gregorian calendar
published annually by the Government Statistics Office (TCTK).

Covered every year:

* ``tet_solar(y)`` — the solar date of 1/1 lunar (Mùng 1 Tết)
* ``gio_to_solar(y)`` — the solar date of 10/3 lunar
  (Giỗ Tổ Hùng Vương)

For years outside [2020, 2035] both functions raise
``LookupError``; callers should bundle their own extension.
"""

from __future__ import annotations

from datetime import date

# Source: TCTK official VN Gregorian calendar publications.
# Verified against vietcalendar.vn and en.wikipedia.org/wiki/Tết.
_TET_TABLE: dict[int, date] = {
    2020: date(2020, 1, 25),
    2021: date(2021, 2, 12),
    2022: date(2022, 2, 1),
    2023: date(2023, 1, 22),
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
    2027: date(2027, 2, 6),
    2028: date(2028, 1, 26),
    2029: date(2029, 2, 13),
    2030: date(2030, 2, 3),
    2031: date(2031, 1, 23),
    2032: date(2032, 2, 11),
    2033: date(2033, 1, 31),
    2034: date(2034, 2, 19),
    2035: date(2035, 2, 8),
}

# Giỗ Tổ Hùng Vương = 10/3 lunar. Source: same TCTK publications.
_GIO_TO_TABLE: dict[int, date] = {
    2020: date(2020, 4, 2),
    2021: date(2021, 4, 21),
    2022: date(2022, 4, 10),
    2023: date(2023, 4, 29),
    2024: date(2024, 4, 18),
    2025: date(2025, 4, 7),
    2026: date(2026, 4, 26),
    2027: date(2027, 4, 16),
    2028: date(2028, 4, 4),
    2029: date(2029, 4, 23),
    2030: date(2030, 4, 12),
    2031: date(2031, 4, 1),
    2032: date(2032, 4, 19),
    2033: date(2033, 4, 8),
    2034: date(2034, 4, 27),
    2035: date(2035, 4, 17),
}


def tet_solar(year: int) -> date:
    """Return the solar date of Mùng 1 Tết for solar ``year``.

    Raises ``LookupError`` for years outside the bundled table.
    """
    if year not in _TET_TABLE:
        raise LookupError(
            f"Tết solar date not bundled for year {year}; "
            f"supported range is {min_year()}-{max_year()}",
        )
    return _TET_TABLE[year]


def gio_to_solar(year: int) -> date:
    """Return the solar date of Giỗ Tổ Hùng Vương for solar ``year``."""
    if year not in _GIO_TO_TABLE:
        raise LookupError(
            f"Giỗ Tổ solar date not bundled for year {year}; "
            f"supported range is {min_year()}-{max_year()}",
        )
    return _GIO_TO_TABLE[year]


def min_year() -> int:
    """The earliest year bundled in the lunar table."""
    return min(_TET_TABLE)


def max_year() -> int:
    """The latest year bundled in the lunar table."""
    return max(_TET_TABLE)


def supported_years() -> tuple[int, ...]:
    """Tuple of years for which Tết / Giỗ Tổ are bundled."""
    return tuple(sorted(_TET_TABLE))


__all__ = [
    "gio_to_solar",
    "max_year",
    "min_year",
    "supported_years",
    "tet_solar",
]
