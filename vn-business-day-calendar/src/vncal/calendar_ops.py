"""Business-day arithmetic over a VN holiday calendar.

A **business day** is a Monday–Friday that is not a Vietnamese
public holiday. The functions here all take an optional
``holidays`` set; when omitted, they auto-load the canonical
Article 112 list for the relevant year(s) from
``vncal.holidays.build_year``.

| Function                                | Behaviour                              |
| --------------------------------------- | -------------------------------------- |
| ``is_business_day(d)``                  | ``True`` if ``d`` is Mon-Fri + not holiday |
| ``next_business_day(d)``                | Next business day on or after ``d``    |
| ``prev_business_day(d)``                | Previous business day on or before ``d`` |
| ``add_business_days(d, n)``             | ``d`` plus ``n`` business days (signed)  |
| ``business_days_between(a, b)``         | Half-open business-day count [a, b)    |

The functions are tolerant: passing dates outside the bundled
lunar table only fails if the resulting calendar needs Tết
information that year.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from vncal.holidays import build_year

if TYPE_CHECKING:
    from datetime import date


def _resolve_holiday_set(
    d: date,
    holidays: set[date] | None,
    extra_years: tuple[int, ...] = (),
) -> set[date]:
    """Build (or accept) a set of holiday dates covering ``d`` and
    any ``extra_years``."""
    if holidays is not None:
        return holidays
    years = {d.year, *extra_years}
    out: set[date] = set()
    for y in years:
        try:
            for h in build_year(y):
                out.add(h.date)
        except LookupError:
            # Year outside bundled range — return what we have.
            pass
    return out


def is_business_day(d: date, *, holidays: set[date] | None = None) -> bool:
    """``True`` if ``d`` is a Mon-Fri AND not a public holiday."""
    if d.weekday() >= 5:
        return False
    hs = _resolve_holiday_set(d, holidays)
    return d not in hs


def next_business_day(d: date, *, holidays: set[date] | None = None) -> date:
    """The next business day on or **after** ``d``."""
    cur = d
    hs = _resolve_holiday_set(cur, holidays, extra_years=(d.year + 1,))
    while cur.weekday() >= 5 or cur in hs:
        cur += timedelta(days=1)
        if cur.year != d.year:
            hs = _resolve_holiday_set(cur, holidays)
    return cur


def prev_business_day(d: date, *, holidays: set[date] | None = None) -> date:
    """The previous business day on or **before** ``d``."""
    cur = d
    hs = _resolve_holiday_set(cur, holidays, extra_years=(d.year - 1,))
    while cur.weekday() >= 5 or cur in hs:
        cur -= timedelta(days=1)
        if cur.year != d.year:
            hs = _resolve_holiday_set(cur, holidays)
    return cur


def add_business_days(
    d: date,
    n: int,
    *,
    holidays: set[date] | None = None,
) -> date:
    """Return the date that is ``n`` business days from ``d``.

    ``n > 0`` walks forward, ``n < 0`` walks backward, ``n == 0``
    returns ``d`` unchanged (even if it's a weekend / holiday).
    """
    if n == 0:
        return d
    cur = d
    step = 1 if n > 0 else -1
    remaining = abs(n)
    hs = _resolve_holiday_set(
        cur,
        holidays,
        extra_years=(d.year - 1, d.year + 1),
    )
    last_year = cur.year
    while remaining > 0:
        cur += timedelta(days=step)
        if cur.year != last_year:
            hs = _resolve_holiday_set(cur, holidays)
            last_year = cur.year
        if cur.weekday() < 5 and cur not in hs:
            remaining -= 1
    return cur


def business_days_between(start: date, end: date, *, holidays: set[date] | None = None) -> int:
    """Count business days in the half-open interval ``[start, end)``.

    Returns a negative count when ``end < start``. ``start == end``
    → 0.
    """
    if start == end:
        return 0
    if end < start:
        return -business_days_between(end, start, holidays=holidays)
    hs = _resolve_holiday_set(
        start,
        holidays,
        extra_years=tuple(range(start.year, end.year + 1)),
    )
    count = 0
    cur = start
    while cur < end:
        if cur.weekday() < 5 and cur not in hs:
            count += 1
        cur += timedelta(days=1)
    return count


__all__ = [
    "add_business_days",
    "business_days_between",
    "is_business_day",
    "next_business_day",
    "prev_business_day",
]
