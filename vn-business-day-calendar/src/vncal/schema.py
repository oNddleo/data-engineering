"""Holiday + calendar schema.

A Vietnamese public-holiday entry per Article 112 of the
**Bộ Luật Lao động 2019** (Labour Code), plus the day-off /
compensation-day extensions announced annually by the Prime
Minister.

Six holiday kinds cover the canonical set:

| Kind             | Meaning                                                   |
| ---------------- | --------------------------------------------------------- |
| ``SOLAR_FIXED``  | Fixed solar (Gregorian) calendar date (e.g. 1 May)        |
| ``LUNAR_FIXED``  | Fixed lunar date converted to solar (e.g. 10/3 lunar)     |
| ``TET``          | Tết Nguyên Đán — 5 consecutive lunar days from 1/1 lunar  |
| ``COMPENSATION`` | Day-off announced by PM when a fixed holiday falls Sat/Sun |
| ``OPTIONAL``     | Optional regional / customary day (not in Article 112)    |
| ``BRIDGE``       | Single Friday/Monday "cầu ngày" bridge between holidays   |

All dates are tz-naive ``date`` objects, interpreted in VN_TZ.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class HolidayKind(str, Enum):
    """Six kinds covering the canonical Vietnamese holiday set."""

    SOLAR_FIXED = "SOLAR_FIXED"  # 1 Jan, 30 Apr, 1 May, 2 Sep
    LUNAR_FIXED = "LUNAR_FIXED"  # Giỗ Tổ Hùng Vương = 10/3 lunar
    TET = "TET"  # Lunar new year — 5 days
    COMPENSATION = "COMPENSATION"  # Sat/Sun → next Mon/Tue
    OPTIONAL = "OPTIONAL"  # International Women's Day, etc
    BRIDGE = "BRIDGE"  # PM-announced bridge weekday


@dataclass(frozen=True, slots=True)
class Holiday:
    """One holiday entry on a specific calendar year."""

    date: date  # the solar date on which it is observed
    name_vi: str  # canonical VN name
    name_en: str  # English gloss
    kind: HolidayKind
    paid: bool = True  # paid public holiday under Article 112?

    def __post_init__(self) -> None:
        if not self.name_vi:
            raise ValueError("name_vi must be non-empty")
        if not self.name_en:
            raise ValueError("name_en must be non-empty")


@dataclass(frozen=True, slots=True)
class FiscalYear:
    """A fiscal-year window — used for billing-cycle math."""

    label: str  # e.g. "FY2026" (calendar) or "FY2025-26" (April-Mar)
    start_date: date  # inclusive
    end_date: date  # inclusive

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label must be non-empty")
        if self.end_date < self.start_date:
            raise ValueError(
                f"end_date {self.end_date} before start_date {self.start_date}",
            )

    def contains(self, d: date) -> bool:
        """``True`` if ``d`` falls in ``[start_date, end_date]``."""
        return self.start_date <= d <= self.end_date

    def days_in_year(self) -> int:
        """Inclusive day-count between start and end."""
        return (self.end_date - self.start_date).days + 1


__all__ = [
    "VN_TZ",
    "FiscalYear",
    "Holiday",
    "HolidayKind",
]
