"""Fiscal-year helpers.

Two flavours bundled:

* **Calendar fiscal year** (the standard for VN private companies) —
  ``[1 Jan, 31 Dec]``. Label: ``"FY2026"``.
* **April-March fiscal year** (the public-sector / many JP-VN joint
  ventures convention) — ``[1 Apr Y, 31 Mar Y+1]``. Label:
  ``"FY2025-26"`` (the year being labelled is the year-end).

Callers needing other conventions can construct ``FiscalYear``
instances directly.
"""

from __future__ import annotations

from datetime import date

from vncal.schema import FiscalYear


def calendar_fy(year: int) -> FiscalYear:
    """``FY<year>`` running 1 Jan – 31 Dec of ``year``."""
    return FiscalYear(
        label=f"FY{year}",
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
    )


def april_march_fy(end_year: int) -> FiscalYear:
    """``FY<end_year-1>-<end_year>`` running 1 Apr (end_year-1) –
    31 Mar (end_year)."""
    return FiscalYear(
        label=f"FY{end_year - 1}-{str(end_year)[-2:]}",
        start_date=date(end_year - 1, 4, 1),
        end_date=date(end_year, 3, 31),
    )


def fiscal_year_for(d: date, *, april_march: bool = False) -> FiscalYear:
    """Return the fiscal year ``d`` falls into."""
    if not april_march:
        return calendar_fy(d.year)
    # April-March: if month >= 4, fiscal year ends next year; else this year.
    end_year = d.year + 1 if d.month >= 4 else d.year
    return april_march_fy(end_year)


__all__ = [
    "april_march_fy",
    "calendar_fy",
    "fiscal_year_for",
]
