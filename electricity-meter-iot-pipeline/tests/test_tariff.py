"""VN 6-tier tariff calculation."""

from __future__ import annotations

import pytest

from evnmeter.tariff import TierBreak, compute_bill, default_tiers


def test_zero_kwh_zero_bill():
    breakdown, subtotal, vat, grand = compute_bill(0)
    assert breakdown == []
    assert subtotal == 0
    assert vat == 0
    assert grand == 0


def test_under_first_tier():
    breakdown, subtotal, vat, grand = compute_bill(30)
    # Only Bậc 1 fires: 30 × 1806 = 54_180.
    assert len(breakdown) == 1
    assert breakdown[0].tier == 1
    assert breakdown[0].kwh == 30
    assert subtotal == 54_180


def test_exactly_first_tier_boundary():
    breakdown, subtotal, _, _ = compute_bill(50)
    # 50 kWh fits entirely in tier 1.
    assert len(breakdown) == 1
    assert breakdown[0].kwh == 50
    assert subtotal == 50 * 1_806


def test_one_above_first_tier():
    breakdown, subtotal, _, _ = compute_bill(51)
    # 50 in tier 1 + 1 in tier 2.
    assert len(breakdown) == 2
    assert breakdown[0].kwh == 50
    assert breakdown[1].kwh == 1
    assert subtotal == 50 * 1_806 + 1 * 1_866


def test_350_kwh_matches_published_example():
    """The 350 kWh example from the README must match exactly."""
    breakdown, subtotal, vat, grand = compute_bill(350)
    assert subtotal == (50 * 1_806 + 50 * 1_866 + 100 * 2_167 + 100 * 2_729 + 50 * 3_050)
    assert subtotal == 825_700
    # 8% VAT on 825,700 = 66,056.
    assert vat == 66_056
    assert grand == 891_756


def test_unbounded_top_tier():
    """Consumption above tier 5 lands in tier 6 at the open-ended rate."""
    breakdown, subtotal, _, _ = compute_bill(500)
    # Tier 6 catches the last 100 kWh.
    tier6 = next(b for b in breakdown if b.tier == 6)
    assert tier6.kwh == 100
    assert tier6.rate_vnd_per_kwh == 3_151


def test_all_tiers_fire_for_high_consumption():
    """A heavy user touches all 6 tiers."""
    breakdown, _, _, _ = compute_bill(500)
    assert {b.tier for b in breakdown} == {1, 2, 3, 4, 5, 6}


def test_breakdown_sums_to_subtotal():
    """Sum of per-tier VND amounts equals subtotal."""
    breakdown, subtotal, _, _ = compute_bill(450)
    assert sum(b.vnd for b in breakdown) == subtotal


def test_validates_negative_kwh():
    with pytest.raises(ValueError):
        compute_bill(-1)


def test_validates_empty_tiers():
    with pytest.raises(ValueError, match="non-empty"):
        compute_bill(100, tiers=())


def test_validates_no_open_tier():
    bad_tiers = (
        TierBreak(tier=1, upper_kwh=50, rate_vnd_per_kwh=1_806),
        TierBreak(tier=2, upper_kwh=100, rate_vnd_per_kwh=1_866),  # bounded
    )
    with pytest.raises(ValueError, match="open-ended"):
        compute_bill(100, tiers=bad_tiers)


def test_custom_vat_bps():
    """Passing a different VAT rate produces a different total."""
    _, sub, vat10, grand10 = compute_bill(100, vat_bps=1000)  # 10%
    _, _, vat8, _ = compute_bill(100, vat_bps=800)
    assert vat10 > vat8
    assert grand10 == sub + vat10


def test_default_tiers_is_defensive_copy():
    """Mutating the returned tuple shouldn't affect future calls (tuples are immutable so this verifies the contract)."""
    t1 = default_tiers()
    t2 = default_tiers()
    assert t1 == t2
    assert len(t1) == 6
