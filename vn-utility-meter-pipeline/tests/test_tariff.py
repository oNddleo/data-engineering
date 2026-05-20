"""EVN tariff schedule + date-based lookup."""

from __future__ import annotations

from datetime import date

import pytest

from evn.tariff import (
    DEFAULT_SCHEDULE,
    SCHEDULE_2023_11,
    SCHEDULE_2024_10,
    FlatTariff,
    HouseholdTariff,
    TariffTier,
    all_schedules,
    tariff_for_date,
)

# ---------- TariffTier -----------------------------------------------------


def test_tariff_tier_basic() -> None:
    t = TariffTier(upper_bound_kwh=50, vnd_per_kwh=1_893)
    assert t.vnd_per_kwh == 1_893


def test_tariff_tier_open_ended() -> None:
    """Last tier has upper_bound_kwh=None."""
    t = TariffTier(upper_bound_kwh=None, vnd_per_kwh=3_302)
    assert t.upper_bound_kwh is None


def test_tariff_tier_rejects_negative_bound() -> None:
    with pytest.raises(ValueError, match="upper_bound_kwh"):
        TariffTier(upper_bound_kwh=-1, vnd_per_kwh=1_000)


def test_tariff_tier_rejects_negative_rate() -> None:
    with pytest.raises(ValueError, match="vnd_per_kwh"):
        TariffTier(upper_bound_kwh=50, vnd_per_kwh=-1)


# ---------- HouseholdTariff ------------------------------------------------


def test_household_tariff_basic() -> None:
    """The default 2024-10 schedule has exactly 6 tiers."""
    assert len(DEFAULT_SCHEDULE.household.tiers) == 6


def test_household_tariff_rejects_empty() -> None:
    with pytest.raises(ValueError, match="tiers"):
        HouseholdTariff(tiers=())


def test_household_tariff_rejects_non_terminal_open_ended() -> None:
    """A non-last tier with upper_bound_kwh=None is invalid."""
    with pytest.raises(ValueError, match="finite"):
        HouseholdTariff(
            tiers=(
                TariffTier(upper_bound_kwh=None, vnd_per_kwh=1_000),
                TariffTier(upper_bound_kwh=None, vnd_per_kwh=2_000),
            )
        )


def test_household_tariff_rejects_unbounded_top() -> None:
    """The top tier must be open-ended."""
    with pytest.raises(ValueError, match="open-ended"):
        HouseholdTariff(
            tiers=(
                TariffTier(upper_bound_kwh=50, vnd_per_kwh=1_000),
                TariffTier(upper_bound_kwh=100, vnd_per_kwh=2_000),
            )
        )


def test_household_tariff_rejects_non_ascending() -> None:
    """Bounds must be strictly ascending."""
    with pytest.raises(ValueError, match="ascending"):
        HouseholdTariff(
            tiers=(
                TariffTier(upper_bound_kwh=100, vnd_per_kwh=1_000),
                TariffTier(upper_bound_kwh=50, vnd_per_kwh=2_000),
                TariffTier(upper_bound_kwh=None, vnd_per_kwh=3_000),
            )
        )


def test_default_schedule_household_first_tier() -> None:
    """2024-10 schedule tier 1: 0-50 kWh @ 1,893 VND/kWh."""
    tier = DEFAULT_SCHEDULE.household.tiers[0]
    assert tier.upper_bound_kwh == 50
    assert tier.vnd_per_kwh == 1_893


def test_default_schedule_household_tier_six_open() -> None:
    """Tier 6 is open-ended."""
    last = DEFAULT_SCHEDULE.household.tiers[-1]
    assert last.upper_bound_kwh is None
    assert last.vnd_per_kwh == 3_302


# ---------- FlatTariff -----------------------------------------------------


def test_flat_tariff_basic() -> None:
    assert FlatTariff(vnd_per_kwh=2_005).vnd_per_kwh == 2_005


def test_flat_tariff_rejects_negative() -> None:
    with pytest.raises(ValueError, match="vnd_per_kwh"):
        FlatTariff(vnd_per_kwh=-1)


# ---------- TariffSchedule -------------------------------------------------


def test_schedule_flat_for_business() -> None:
    from evn.schema import CustomerCategory

    flat = DEFAULT_SCHEDULE.flat_for(CustomerCategory.BUSINESS)
    assert flat.vnd_per_kwh == 2_752


def test_schedule_flat_for_household_raises() -> None:
    """HOUSEHOLD doesn't have a flat tariff — should raise."""
    from evn.schema import CustomerCategory

    with pytest.raises(ValueError, match="HOUSEHOLD"):
        DEFAULT_SCHEDULE.flat_for(CustomerCategory.HOUSEHOLD)


def test_default_schedule_is_2024_10() -> None:
    assert DEFAULT_SCHEDULE.effective_from == date(2024, 10, 11)
    assert DEFAULT_SCHEDULE.decision == "2699/QĐ-BCT"


# ---------- tariff_for_date ------------------------------------------------


def test_tariff_for_date_after_latest() -> None:
    """Any date >= 2024-10-11 returns SCHEDULE_2024_10."""
    assert tariff_for_date(date(2025, 5, 1)) is SCHEDULE_2024_10
    assert tariff_for_date(date(2024, 10, 11)) is SCHEDULE_2024_10


def test_tariff_for_date_between_schedules() -> None:
    """Dates between 2023-11-09 and 2024-10-10 return SCHEDULE_2023_11."""
    assert tariff_for_date(date(2024, 5, 1)) is SCHEDULE_2023_11


def test_tariff_for_date_before_earliest() -> None:
    """Dates before any bundled schedule fall back to the earliest."""
    assert tariff_for_date(date(2020, 1, 1)) is SCHEDULE_2023_11


def test_all_schedules_sorted() -> None:
    scheds = all_schedules()
    for i in range(1, len(scheds)):
        assert scheds[i - 1].effective_from <= scheds[i].effective_from


def test_all_schedules_count() -> None:
    """We bundle 2 schedules currently."""
    assert len(all_schedules()) == 2
