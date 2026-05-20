"""Annual aggregator: per-customer rollup of bills."""

from __future__ import annotations

from datetime import date

import pytest

from evn.aggregator import aggregate_annual
from evn.billing import compute_bill
from evn.schema import CustomerCategory

from ._fixtures import make_reading


def _bills_for_customer(customer_code: str, n_months: int = 6) -> list:
    """Build N bills for the given customer."""
    return [
        compute_bill(
            make_reading(
                customer_code=customer_code,
                period_start=date(2025, m + 1, 1),
                period_end=date(2025, m + 1, 28),
                kwh_used=100 + 10 * m,
            )
        )
        for m in range(n_months)
    ]


def test_aggregate_single_customer() -> None:
    bills = _bills_for_customer("PA00000000001", n_months=6)
    summaries = aggregate_annual(bills)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.customer_code == "PA00000000001"
    assert s.n_bills == 6
    assert s.total_kwh == sum(100 + 10 * m for m in range(6))


def test_aggregate_multiple_customers() -> None:
    bills = _bills_for_customer("PA00000000001", n_months=3) + _bills_for_customer(
        "PE99999999999", n_months=3
    )
    summaries = aggregate_annual(bills)
    assert len(summaries) == 2
    assert {s.customer_code for s in summaries} == {
        "PA00000000001",
        "PE99999999999",
    }


def test_aggregate_amounts_sum() -> None:
    bills = _bills_for_customer("PA00000000001", n_months=4)
    s = aggregate_annual(bills)[0]
    assert s.total_pre_vat_vnd == sum(b.pre_vat_amount_vnd for b in bills)
    assert s.total_vat_vnd == sum(b.vat_amount_vnd for b in bills)


def test_aggregate_total_includes_vat() -> None:
    bills = _bills_for_customer("PA00000000001", n_months=3)
    s = aggregate_annual(bills)[0]
    assert s.total_amount_vnd == s.total_pre_vat_vnd + s.total_vat_vnd


def test_aggregate_average_kwh() -> None:
    bills = _bills_for_customer("PA00000000001", n_months=6)
    s = aggregate_annual(bills)[0]
    assert s.average_kwh_per_bill == s.total_kwh / 6


def test_aggregate_sorted_by_customer() -> None:
    bills = _bills_for_customer("PE99999999999") + _bills_for_customer("PA00000000001")
    summaries = aggregate_annual(bills)
    assert [s.customer_code for s in summaries] == [
        "PA00000000001",
        "PE99999999999",
    ]


def test_aggregate_rejects_mixed_categories() -> None:
    """One customer can't appear with two different categories."""
    b1 = compute_bill(
        make_reading(
            customer_code="PA00000000001",
            category=CustomerCategory.HOUSEHOLD,
            kwh_used=100,
        )
    )
    b2 = compute_bill(
        make_reading(
            customer_code="PA00000000001",
            category=CustomerCategory.BUSINESS,
            kwh_used=500,
        )
    )
    with pytest.raises(ValueError, match="mixed categories"):
        aggregate_annual([b1, b2])


def test_aggregate_empty() -> None:
    assert aggregate_annual([]) == []


def test_aggregate_zero_division_safe() -> None:
    """average_kwh_per_bill must not divide by zero."""
    from evn.aggregator import AnnualSummary

    s = AnnualSummary(
        customer_code="PA00000000001",
        category=CustomerCategory.HOUSEHOLD,
        n_bills=0,
        total_kwh=0,
        total_pre_vat_vnd=0,
        total_vat_vnd=0,
    )
    assert s.average_kwh_per_bill == 0.0
