"""Hypothesis properties — invariants of calendar arithmetic."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from vncal.calendar_ops import (
    add_business_days,
    business_days_between,
    is_business_day,
    next_business_day,
    prev_business_day,
)
from vncal.fiscal import calendar_fy, fiscal_year_for
from vncal.holidays import build_year
from vncal.lunar import max_year, min_year, tet_solar

_BUNDLED_DATES = st.dates(
    min_value=date(min_year(), 1, 1),
    max_value=date(max_year(), 12, 31),
)


@given(_BUNDLED_DATES)
@settings(max_examples=40)
def test_property_business_day_excludes_weekends(d: date) -> None:
    """A Saturday or Sunday is never a business day."""
    if d.weekday() >= 5:
        assert is_business_day(d) is False


@given(_BUNDLED_DATES)
@settings(max_examples=30)
def test_property_next_business_day_is_business_day(d: date) -> None:
    """The result of next_business_day is always a business day."""
    out = next_business_day(d)
    assert is_business_day(out)


@given(_BUNDLED_DATES)
@settings(max_examples=30)
def test_property_prev_business_day_is_business_day(d: date) -> None:
    """The result of prev_business_day is always a business day."""
    out = prev_business_day(d)
    assert is_business_day(out)


@given(
    d=_BUNDLED_DATES,
    n=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_add_business_days_lands_on_business_day(d: date, n: int) -> None:
    """add_business_days with non-zero n always lands on a business day."""
    out = add_business_days(d, n)
    assert is_business_day(out)


@given(
    d=_BUNDLED_DATES,
    n=st.integers(min_value=1, max_value=30),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_add_business_days_inverse(d: date, n: int) -> None:
    """For business-day d, add(add(d, n), -n) == d.

    (When d is non-business, the round-trip lands on a different business day.)
    """
    assume(is_business_day(d))
    forward = add_business_days(d, n)
    back = add_business_days(forward, -n)
    assert back == d


@given(
    a=_BUNDLED_DATES,
    b=_BUNDLED_DATES,
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_property_business_days_between_anti_symmetric(a: date, b: date) -> None:
    """business_days_between(a, b) == -business_days_between(b, a)."""
    assert business_days_between(a, b) == -business_days_between(b, a)


@given(
    d=_BUNDLED_DATES,
    n=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_business_days_between_consistent_with_add(
    d: date,
    n: int,
) -> None:
    """For business-day d, business_days_between(d, add(d, n)) == n."""
    assume(is_business_day(d))
    forward = add_business_days(d, n)
    assert business_days_between(d, forward) == n


@given(
    d=_BUNDLED_DATES,
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_calendar_fy_contains_d(d: date) -> None:
    """``calendar_fy(d.year)`` always contains ``d``."""
    fy = calendar_fy(d.year)
    assert fy.contains(d)


@given(
    d=_BUNDLED_DATES,
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_fiscal_year_for_contains_d(d: date) -> None:
    """``fiscal_year_for(d)`` always contains ``d`` (both modes)."""
    fy_cal = fiscal_year_for(d, april_march=False)
    fy_am = fiscal_year_for(d, april_march=True)
    assert fy_cal.contains(d)
    assert fy_am.contains(d)


@given(
    year=st.integers(min_value=min_year(), max_value=max_year()),
)
@settings(max_examples=10)
def test_property_tet_block_consecutive(year: int) -> None:
    """The 5-day Tết block is always five consecutive days from the eve."""
    holidays = build_year(year)
    tet_block = sorted(h.date for h in holidays if h.kind.value == "TET")
    assert len(tet_block) == 5
    for prev, curr in pairwise(tet_block):
        assert (curr - prev) == timedelta(days=1)


@given(
    year=st.integers(min_value=min_year(), max_value=max_year()),
)
@settings(max_examples=10)
def test_property_tet_eve_one_day_before_mung_1(year: int) -> None:
    """The eve (first day of the Tết block) is the day before tet_solar(year)."""
    holidays = build_year(year)
    tet_block = sorted(h.date for h in holidays if h.kind.value == "TET")
    assert tet_block[0] == tet_solar(year) - timedelta(days=1)
