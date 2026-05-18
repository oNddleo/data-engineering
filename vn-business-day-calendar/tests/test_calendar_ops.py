"""Business-day arithmetic."""

from __future__ import annotations

from datetime import date

from vncal.calendar_ops import (
    add_business_days,
    business_days_between,
    is_business_day,
    next_business_day,
    prev_business_day,
)

# ---------- is_business_day --------------------------------------------------


def test_is_business_day_weekday():
    """Mon 2026-05-18 is a business day."""
    assert is_business_day(date(2026, 5, 18)) is True


def test_is_business_day_saturday():
    assert is_business_day(date(2026, 5, 16)) is False


def test_is_business_day_sunday():
    assert is_business_day(date(2026, 5, 17)) is False


def test_is_business_day_tet():
    """Tết Mùng 1 (2026-02-17, Tue) is NOT a business day."""
    assert is_business_day(date(2026, 2, 17)) is False


def test_is_business_day_quoc_khanh():
    """2 Sep 2026 (Wed) is NOT a business day."""
    assert is_business_day(date(2026, 9, 2)) is False


def test_is_business_day_with_explicit_holiday_set():
    custom = {date(2026, 5, 18)}
    assert is_business_day(date(2026, 5, 18), holidays=custom) is False


# ---------- next_business_day ------------------------------------------------


def test_next_business_day_after_friday():
    """Fri → Mon (skip weekend)."""
    fri = date(2026, 5, 22)
    assert next_business_day(fri + (date(2026, 5, 23) - fri)) == date(2026, 5, 25)


def test_next_business_day_on_business_day_returns_same():
    """Calling on a Monday returns the same Monday."""
    mon = date(2026, 5, 18)
    assert next_business_day(mon) == mon


def test_next_business_day_skips_tet():
    """Sat 14 Feb 2026 → next business day = Mon 23 Feb (after 5-day Tết)."""
    sat = date(2026, 2, 14)
    out = next_business_day(sat)
    # Tết block is Mon 16 - Fri 20 Feb. Sat 21 / Sun 22 are weekend. Mon 23 Feb.
    assert out == date(2026, 2, 23)


# ---------- prev_business_day ------------------------------------------------


def test_prev_business_day_before_monday():
    """Mon → Fri (skip weekend)."""
    sun = date(2026, 5, 17)
    assert prev_business_day(sun) == date(2026, 5, 15)


def test_prev_business_day_on_business_day_returns_same():
    mon = date(2026, 5, 18)
    assert prev_business_day(mon) == mon


# ---------- add_business_days ------------------------------------------------


def test_add_business_days_zero():
    """n=0 returns d unchanged even if d is weekend."""
    sat = date(2026, 5, 16)
    assert add_business_days(sat, 0) == sat


def test_add_business_days_positive():
    """Mon + 5 business days = next Mon (Mon+7 calendar)."""
    mon = date(2026, 5, 18)
    assert add_business_days(mon, 5) == date(2026, 5, 25)


def test_add_business_days_skip_weekend():
    """Mon 5/18 + 1 = Tue 5/19."""
    assert add_business_days(date(2026, 5, 18), 1) == date(2026, 5, 19)


def test_add_business_days_skip_holiday():
    """Mon 27 Apr 2026 = Bù Giỗ Tổ (comp day) → skip."""
    # Fri 24 Apr 2026 + 1 business day. Sat/Sun + Sun 26 Apr Giỗ Tổ + Mon 27 Apr comp.
    # First business day after Fri 24 Apr = Tue 28 Apr.
    assert add_business_days(date(2026, 4, 24), 1) == date(2026, 4, 28)


def test_add_business_days_negative():
    """Mon - 1 business day = previous Friday."""
    mon = date(2026, 5, 18)
    assert add_business_days(mon, -1) == date(2026, 5, 15)


def test_add_business_days_across_year():
    """31 Dec 2025 + 1 business day. 1 Jan 2026 = Tết Dương Lịch → skip.
    First business day = Fri 2 Jan 2026."""
    out = add_business_days(date(2025, 12, 31), 1)
    assert out == date(2026, 1, 2)


# ---------- business_days_between --------------------------------------------


def test_between_same_day():
    assert business_days_between(date(2026, 5, 18), date(2026, 5, 18)) == 0


def test_between_one_week():
    """Mon → next Mon = 5 business days (Mon, Tue, Wed, Thu, Fri)."""
    mon = date(2026, 5, 18)
    next_mon = date(2026, 5, 25)
    assert business_days_between(mon, next_mon) == 5


def test_between_with_holiday_block():
    """Mon 16 Feb 2026 → Mon 23 Feb (8 cal days, but 5 are Tết)."""
    assert business_days_between(date(2026, 2, 16), date(2026, 2, 23)) == 0


def test_between_negative_when_reversed():
    """end < start returns a negative count."""
    a = date(2026, 5, 18)
    b = date(2026, 5, 25)
    assert business_days_between(b, a) == -5


def test_between_half_open_range():
    """[Mon, Tue) = 1 business day (only Mon)."""
    assert business_days_between(date(2026, 5, 18), date(2026, 5, 19)) == 1
