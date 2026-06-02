"""Progressive-tier billing engine + VAT."""

from __future__ import annotations

from evn.billing import compute_bill
from evn.schema import CustomerCategory
from evn.tariff import DEFAULT_SCHEDULE

from ._fixtures import make_reading

# ---------- Household progressive tiers ------------------------------------


def test_bill_household_tier_one_only() -> None:
    """A 40-kWh bill stays entirely in tier 1 (0-50 @ 1893)."""
    bill = compute_bill(make_reading(kwh_used=40))
    assert len(bill.tier_breakdown) == 1
    assert bill.tier_breakdown[0].tier_index == 1
    assert bill.tier_breakdown[0].kwh == 40
    assert bill.tier_breakdown[0].amount_vnd == 40 * 1_893
    assert bill.pre_vat_amount_vnd == 40 * 1_893


def test_bill_household_two_tiers() -> None:
    """A 100-kWh bill spans tiers 1 and 2 exactly."""
    bill = compute_bill(make_reading(kwh_used=100))
    assert len(bill.tier_breakdown) == 2
    assert bill.tier_breakdown[0].kwh == 50
    assert bill.tier_breakdown[1].kwh == 50
    expected = 50 * 1_893 + 50 * 1_956
    assert bill.pre_vat_amount_vnd == expected


def test_bill_household_all_six_tiers() -> None:
    """A 500-kWh bill exercises all six tiers."""
    bill = compute_bill(make_reading(kwh_used=500))
    assert len(bill.tier_breakdown) == 6
    expected = (
        50 * 1_893  # tier 1: 0-50
        + 50 * 1_956  # tier 2: 51-100
        + 100 * 2_271  # tier 3: 101-200
        + 100 * 2_860  # tier 4: 201-300
        + 100 * 3_197  # tier 5: 301-400
        + 100 * 3_302  # tier 6: 401-500
    )
    assert bill.pre_vat_amount_vnd == expected


def test_bill_household_zero_kwh() -> None:
    """A 0-kWh household reading produces a zero bill with no breakdown rows."""
    bill = compute_bill(make_reading(kwh_used=0))
    assert bill.tier_breakdown == ()
    assert bill.pre_vat_amount_vnd == 0
    assert bill.vat_amount_vnd == 0


def test_bill_household_partial_top_tier() -> None:
    """450 kWh = 400 in tiers 1-5 + 50 in tier 6."""
    bill = compute_bill(make_reading(kwh_used=450))
    assert len(bill.tier_breakdown) == 6
    assert bill.tier_breakdown[5].kwh == 50


# ---------- Flat-category bills --------------------------------------------


def test_bill_business_flat() -> None:
    """BUSINESS rate is 2,752 VND/kWh (default 2024-10 schedule)."""
    bill = compute_bill(
        make_reading(
            category=CustomerCategory.BUSINESS,
            kwh_used=1_000,
        )
    )
    assert bill.pre_vat_amount_vnd == 1_000 * 2_752
    assert bill.tier_breakdown == ()


def test_bill_admin_public_flat() -> None:
    bill = compute_bill(
        make_reading(
            category=CustomerCategory.ADMIN_PUBLIC,
            kwh_used=500,
        )
    )
    assert bill.pre_vat_amount_vnd == 500 * 2_005


def test_bill_production_flat() -> None:
    bill = compute_bill(
        make_reading(
            category=CustomerCategory.PRODUCTION,
            kwh_used=5_000,
        )
    )
    assert bill.pre_vat_amount_vnd == 5_000 * 2_159


def test_bill_agriculture_flat() -> None:
    bill = compute_bill(
        make_reading(
            category=CustomerCategory.AGRICULTURE,
            kwh_used=2_000,
        )
    )
    assert bill.pre_vat_amount_vnd == 2_000 * 1_644


# ---------- VAT ------------------------------------------------------------


def test_bill_vat_is_ten_percent() -> None:
    """VAT must be exactly 10% of the pre-VAT amount (rounded up)."""
    bill = compute_bill(make_reading(kwh_used=100))
    expected_vat = (bill.pre_vat_amount_vnd * 1_000 + 9_999) // 10_000
    assert bill.vat_amount_vnd == expected_vat


def test_bill_total_includes_vat() -> None:
    bill = compute_bill(make_reading(kwh_used=200))
    assert bill.total_amount_vnd == bill.pre_vat_amount_vnd + bill.vat_amount_vnd


# ---------- Schedule override ----------------------------------------------


def test_bill_with_2023_11_schedule() -> None:
    """Passing the older schedule explicitly uses its rates."""
    from evn.tariff import SCHEDULE_2023_11

    bill = compute_bill(make_reading(kwh_used=40), schedule=SCHEDULE_2023_11)
    # Tier 1 at 1,806 VND/kWh under the Nov-2023 schedule.
    assert bill.pre_vat_amount_vnd == 40 * 1_806


def test_default_schedule_used_when_not_specified() -> None:
    bill_default = compute_bill(make_reading(kwh_used=40))
    bill_explicit = compute_bill(make_reading(kwh_used=40), schedule=DEFAULT_SCHEDULE)
    assert bill_default.pre_vat_amount_vnd == bill_explicit.pre_vat_amount_vnd
