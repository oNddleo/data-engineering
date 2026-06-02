"""Hypothesis property tests for EVN billing invariants."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from evn.aggregator import aggregate_annual
from evn.billing import compute_bill
from evn.customer import is_valid_customer_code
from evn.io_jsonl import (
    bill_from_dict,
    bill_to_dict,
    reading_from_dict,
    reading_to_dict,
)
from evn.schema import CustomerCategory, MeterReading
from evn.tariff import DEFAULT_SCHEDULE, all_schedules, tariff_for_date

_PREFIXES = ("PA", "PB", "PC", "PD", "PE")


@st.composite
def reading_strategy(draw: st.DrawFn) -> MeterReading:
    prefix = draw(st.sampled_from(_PREFIXES))
    suffix = draw(st.integers(min_value=0, max_value=10**11 - 1))
    customer_code = f"{prefix}{suffix:011d}"
    month = draw(st.integers(min_value=1, max_value=12))
    return MeterReading(
        customer_code=customer_code,
        category=draw(st.sampled_from(list(CustomerCategory))),
        period_start=date(2025, month, 1),
        period_end=date(2025, month, 28),
        kwh_used=draw(st.integers(min_value=0, max_value=100_000)),
    )


# ---------- Billing invariants --------------------------------------------


@given(reading_strategy())
@settings(max_examples=80)
def test_bill_amounts_non_negative(r: MeterReading) -> None:
    bill = compute_bill(r)
    assert bill.pre_vat_amount_vnd >= 0
    assert bill.vat_amount_vnd >= 0
    assert bill.total_amount_vnd >= 0


@given(reading_strategy())
@settings(max_examples=80)
def test_bill_total_consistent(r: MeterReading) -> None:
    bill = compute_bill(r)
    assert bill.total_amount_vnd == bill.pre_vat_amount_vnd + bill.vat_amount_vnd


@given(reading_strategy())
@settings(max_examples=80)
def test_bill_kwh_preserved(r: MeterReading) -> None:
    """kwh_used round-trips into the bill unchanged."""
    bill = compute_bill(r)
    assert bill.kwh_used == r.kwh_used


@given(
    st.integers(min_value=0, max_value=1_000_000),
)
@settings(max_examples=50)
def test_household_bill_tier_sums(kwh: int) -> None:
    """Household tier kWh sums equal kwh_used; tier amounts sum to pre-VAT."""
    r = MeterReading(
        customer_code="PA00000000001",
        category=CustomerCategory.HOUSEHOLD,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 28),
        kwh_used=kwh,
    )
    bill = compute_bill(r)
    if kwh == 0:
        assert bill.tier_breakdown == ()
    else:
        tier_kwh = sum(t.kwh for t in bill.tier_breakdown)
        tier_amount = sum(t.amount_vnd for t in bill.tier_breakdown)
        assert tier_kwh == kwh
        assert tier_amount == bill.pre_vat_amount_vnd


@given(
    st.sampled_from(
        [
            CustomerCategory.BUSINESS,
            CustomerCategory.ADMIN_PUBLIC,
            CustomerCategory.PRODUCTION,
            CustomerCategory.AGRICULTURE,
        ]
    ),
    st.integers(min_value=0, max_value=1_000_000),
)
@settings(max_examples=40)
def test_flat_bill_is_simple_product(category: CustomerCategory, kwh: int) -> None:
    """Flat-category pre-VAT amount is exactly kwh × rate."""
    r = MeterReading(
        customer_code="PA00000000001",
        category=category,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 28),
        kwh_used=kwh,
    )
    bill = compute_bill(r)
    rate = DEFAULT_SCHEDULE.flat_for(category).vnd_per_kwh
    assert bill.pre_vat_amount_vnd == kwh * rate
    assert bill.tier_breakdown == ()


@given(
    st.integers(min_value=0, max_value=100_000),
    st.integers(min_value=0, max_value=100_000),
)
@settings(max_examples=40)
def test_household_bill_monotone_in_kwh(kwh_a: int, kwh_b: int) -> None:
    """Higher consumption → higher (or equal) bill."""
    cust = "PA00000000001"
    a = compute_bill(
        MeterReading(
            customer_code=cust,
            category=CustomerCategory.HOUSEHOLD,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 28),
            kwh_used=min(kwh_a, kwh_b),
        )
    )
    b = compute_bill(
        MeterReading(
            customer_code=cust,
            category=CustomerCategory.HOUSEHOLD,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 28),
            kwh_used=max(kwh_a, kwh_b),
        )
    )
    assert b.pre_vat_amount_vnd >= a.pre_vat_amount_vnd


# ---------- JSONL round-trip -----------------------------------------------


@given(reading_strategy())
@settings(max_examples=40)
def test_reading_jsonl_roundtrip(r: MeterReading) -> None:
    assert reading_from_dict(reading_to_dict(r)) == r


@given(reading_strategy())
@settings(max_examples=40)
def test_bill_jsonl_roundtrip(r: MeterReading) -> None:
    bill = compute_bill(r)
    assert bill_from_dict(bill_to_dict(bill)) == bill


# ---------- Aggregator conservation ---------------------------------------


@given(st.lists(reading_strategy(), min_size=1, max_size=30))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_aggregator_kwh_sum_conserves(readings: list[MeterReading]) -> None:
    """Sum of summary.total_kwh equals sum of reading.kwh_used (per group)."""
    seen: set[str] = set()
    unique: list[MeterReading] = []
    cat_by_customer: dict[str, CustomerCategory] = {}
    for r in readings:
        key = (r.customer_code, r.period_start.isoformat())
        if key in seen:
            continue
        # Force the same category per customer for the test invariant.
        existing_cat = cat_by_customer.get(r.customer_code)
        if existing_cat is not None and existing_cat is not r.category:
            r = MeterReading(  # type: ignore[misc]
                customer_code=r.customer_code,
                category=existing_cat,
                period_start=r.period_start,
                period_end=r.period_end,
                kwh_used=r.kwh_used,
            )
        cat_by_customer[r.customer_code] = r.category
        seen.add(key)
        unique.append(r)

    bills = [compute_bill(r) for r in unique]
    summaries = aggregate_annual(bills)
    total_summary_kwh = sum(s.total_kwh for s in summaries)
    total_reading_kwh = sum(r.kwh_used for r in unique)
    assert total_summary_kwh == total_reading_kwh


# ---------- Tariff lookup --------------------------------------------------


@given(
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
@settings(max_examples=50)
def test_tariff_for_date_returns_bundled(d: date) -> None:
    """Every date resolves to one of the bundled schedules."""
    sched = tariff_for_date(d)
    assert sched in all_schedules()


@given(
    st.dates(min_value=date(2024, 10, 11), max_value=date(2030, 1, 1)),
)
@settings(max_examples=40)
def test_tariff_after_2024_uses_default(d: date) -> None:
    assert tariff_for_date(d) is DEFAULT_SCHEDULE


# ---------- Customer code validation ---------------------------------------


@given(st.sampled_from(_PREFIXES), st.integers(min_value=0, max_value=10**11 - 1))
def test_valid_customer_codes_pass(prefix: str, suffix: int) -> None:
    code = f"{prefix}{suffix:011d}"
    assert is_valid_customer_code(code) is True


@given(st.text(min_size=1, max_size=12))
def test_short_codes_fail(s: str) -> None:
    """Anything shorter than 13 chars fails."""
    if len(s) >= 13:
        return
    assert is_valid_customer_code(s) is False


# ---------- Empty / edge invariants ----------------------------------------


def test_period_one_day() -> None:
    """A single-day period is valid (period_end == period_start)."""
    r = MeterReading(
        customer_code="PA00000000001",
        category=CustomerCategory.HOUSEHOLD,
        period_start=date(2025, 1, 15),
        period_end=date(2025, 1, 15),
        kwh_used=0,
    )
    assert r.period_end == r.period_start


def test_period_one_month_dt() -> None:
    """Smoke: a one-month period builds without trouble."""
    r = MeterReading(
        customer_code="PA00000000001",
        category=CustomerCategory.HOUSEHOLD,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 1) + timedelta(days=27),
        kwh_used=100,
    )
    assert (r.period_end - r.period_start).days == 27
