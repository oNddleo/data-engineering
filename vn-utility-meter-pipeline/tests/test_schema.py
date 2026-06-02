"""Schema validation: MeterReading, ElectricityBill, TierUsage."""

from __future__ import annotations

from datetime import date

import pytest

from evn.schema import (
    VAT_BPS,
    AnomalyKind,
    CustomerCategory,
    ElectricityBill,
    TierUsage,
)

from ._fixtures import make_reading

# ---------- MeterReading ---------------------------------------------------


def test_reading_basic() -> None:
    r = make_reading()
    assert r.kwh_used == 150
    assert r.category is CustomerCategory.HOUSEHOLD


def test_reading_rejects_empty_code() -> None:
    with pytest.raises(ValueError, match="customer_code"):
        make_reading(customer_code="")


def test_reading_rejects_negative_kwh() -> None:
    with pytest.raises(ValueError, match="kwh_used"):
        make_reading(kwh_used=-1)


def test_reading_rejects_backwards_period() -> None:
    with pytest.raises(ValueError, match="period_end"):
        make_reading(
            period_start=date(2025, 1, 28),
            period_end=date(2025, 1, 1),
        )


def test_reading_zero_kwh_allowed() -> None:
    """A zero-kWh reading is valid (vacant property or end-of-month)."""
    r = make_reading(kwh_used=0)
    assert r.kwh_used == 0


# ---------- Categories + Anomalies enums -----------------------------------


def test_categories_complete() -> None:
    assert {c.value for c in CustomerCategory} == {
        "HOUSEHOLD",
        "BUSINESS",
        "ADMIN_PUBLIC",
        "PRODUCTION",
        "AGRICULTURE",
    }


def test_anomaly_kinds_complete() -> None:
    assert {k.value for k in AnomalyKind} == {
        "ZERO_USAGE",
        "SUDDEN_DROP",
        "UNREALISTIC_SPIKE",
    }


# ---------- TierUsage ------------------------------------------------------


def test_tier_usage_basic() -> None:
    t = TierUsage(tier_index=1, kwh=50, rate_vnd_per_kwh=1_893, amount_vnd=94_650)
    assert t.amount_vnd == 94_650


def test_tier_usage_rejects_negative_tier_index() -> None:
    with pytest.raises(ValueError, match="tier_index"):
        TierUsage(tier_index=0, kwh=10, rate_vnd_per_kwh=1_000, amount_vnd=10_000)


def test_tier_usage_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount_vnd"):
        TierUsage(tier_index=1, kwh=10, rate_vnd_per_kwh=100, amount_vnd=-1)


# ---------- ElectricityBill ------------------------------------------------


def _make_household_bill(**overrides: object) -> ElectricityBill:
    tiers = (
        TierUsage(tier_index=1, kwh=50, rate_vnd_per_kwh=1_893, amount_vnd=94_650),
        TierUsage(tier_index=2, kwh=50, rate_vnd_per_kwh=1_956, amount_vnd=97_800),
    )
    defaults = {
        "customer_code": "PA00000000001",
        "category": CustomerCategory.HOUSEHOLD,
        "period_start": date(2025, 1, 1),
        "period_end": date(2025, 1, 28),
        "kwh_used": 100,
        "pre_vat_amount_vnd": 192_450,
        "vat_amount_vnd": 19_245,
        "tier_breakdown": tiers,
    }
    defaults.update(overrides)
    return ElectricityBill(**defaults)  # type: ignore[arg-type]


def test_bill_total_includes_vat() -> None:
    b = _make_household_bill()
    assert b.total_amount_vnd == 192_450 + 19_245


def test_bill_tier_sum_must_match_pre_vat() -> None:
    """The breakdown sum must equal pre_vat_amount_vnd."""
    with pytest.raises(ValueError, match="tier breakdown"):
        _make_household_bill(pre_vat_amount_vnd=200_000)  # mismatch


def test_bill_tier_kwh_must_match_total() -> None:
    """The tier kWh sum must equal kwh_used."""
    with pytest.raises(ValueError, match="tier kWh"):
        _make_household_bill(kwh_used=200)  # mismatch


def test_bill_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError, match="pre_vat_amount_vnd"):
        _make_household_bill(pre_vat_amount_vnd=-1, tier_breakdown=())
    with pytest.raises(ValueError, match="vat_amount_vnd"):
        _make_household_bill(vat_amount_vnd=-1, tier_breakdown=())


def test_bill_flat_category_no_breakdown() -> None:
    """BUSINESS bills carry no tier breakdown — single flat rate."""
    b = ElectricityBill(
        customer_code="PA00000000001",
        category=CustomerCategory.BUSINESS,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 28),
        kwh_used=1_000,
        pre_vat_amount_vnd=2_752_000,
        vat_amount_vnd=275_200,
        tier_breakdown=(),
    )
    assert b.tier_breakdown == ()


# ---------- VAT constant ---------------------------------------------------


def test_vat_bps_is_ten_percent() -> None:
    assert VAT_BPS == 1_000
