"""KPI views over FactSellerDay."""

from __future__ import annotations

import pytest

from sellermart.kpis import (
    daily_trend,
    seller_summary,
    top_sellers_by_gmv,
    worst_sellers_by_return_rate,
)
from sellermart.schema import FactSellerDay


def _fact(
    seller_id: int,
    date_key: int,
    n_orders: int,
    gmv: int,
    n_returns: int = 0,
    refund: int = 0,
    n_reviews: int = 0,
    sum_rating: int = 0,
    buyers: int | None = None,
) -> FactSellerDay:
    return FactSellerDay(
        seller_id=seller_id,
        date_key=date_key,
        n_orders=n_orders,
        n_units=n_orders * 2,
        gmv_vnd=gmv,
        n_returns=n_returns,
        refund_vnd=refund,
        n_reviews=n_reviews,
        sum_rating_x100=sum_rating,
        n_unique_buyers=buyers if buyers is not None else n_orders,
    )


def test_summary_rolls_up_per_seller():
    rows = [
        _fact(100_001, 20260501, n_orders=10, gmv=1_000_000),
        _fact(100_001, 20260502, n_orders=15, gmv=1_500_000),
        _fact(100_002, 20260501, n_orders=5, gmv=500_000),
    ]
    summaries = seller_summary(rows)
    assert summaries[100_001].n_orders == 25
    assert summaries[100_001].n_days_active == 2
    assert summaries[100_001].gmv_vnd == 2_500_000
    assert summaries[100_002].n_orders == 5


def test_aov_zero_when_no_orders_in_view():
    """A view with no rows for a seller has aov = 0 (defensive)."""
    summaries = seller_summary([_fact(100_001, 20260501, n_orders=0, gmv=0)])
    assert summaries[100_001].aov_vnd == 0


def test_aov_floor_divides():
    rows = [_fact(100_001, 20260501, n_orders=3, gmv=1_000)]
    summaries = seller_summary(rows)
    assert summaries[100_001].aov_vnd == 333  # 1000 // 3


def test_return_rate_zero_when_no_orders():
    summaries = seller_summary([_fact(100_001, 20260501, n_orders=0, gmv=0)])
    assert summaries[100_001].return_rate_pct == 0.0


def test_return_rate_computed():
    rows = [_fact(100_001, 20260501, n_orders=10, gmv=1_000_000, n_returns=2)]
    summaries = seller_summary(rows)
    assert summaries[100_001].return_rate_pct == 20.0


def test_refund_rate_computed():
    rows = [_fact(100_001, 20260501, n_orders=10, gmv=1_000_000, refund=150_000)]
    summaries = seller_summary(rows)
    assert summaries[100_001].refund_rate_pct == 15.0


def test_refund_rate_zero_when_no_gmv():
    summaries = seller_summary([_fact(100_001, 20260501, n_orders=0, gmv=0)])
    assert summaries[100_001].refund_rate_pct == 0.0


def test_avg_rating_zero_when_no_reviews():
    summaries = seller_summary([_fact(100_001, 20260501, n_orders=10, gmv=1_000_000)])
    assert summaries[100_001].avg_rating_x100 == 0.0


def test_avg_rating_computed():
    rows = [_fact(100_001, 20260501, n_orders=10, gmv=1_000_000, n_reviews=4, sum_rating=1800)]
    summaries = seller_summary(rows)
    assert summaries[100_001].avg_rating_x100 == 450.0


def test_nps_proxy_zero_with_no_reviews():
    summaries = seller_summary([_fact(100_001, 20260501, n_orders=10, gmv=1_000_000)])
    assert summaries[100_001].nps_proxy == 0.0


def test_nps_proxy_at_5_stars_is_100():
    rows = [_fact(100_001, 20260501, n_orders=10, gmv=1_000_000, n_reviews=2, sum_rating=1000)]
    summaries = seller_summary(rows)
    assert summaries[100_001].nps_proxy == 100.0


def test_nps_proxy_at_2_stars_is_minus_100():
    rows = [_fact(100_001, 20260501, n_orders=10, gmv=1_000_000, n_reviews=2, sum_rating=400)]
    summaries = seller_summary(rows)
    assert summaries[100_001].nps_proxy == -100.0


def test_top_sellers_orders_by_gmv_desc():
    rows = [
        _fact(100_001, 20260501, n_orders=10, gmv=1_000_000),
        _fact(100_002, 20260501, n_orders=10, gmv=2_000_000),
        _fact(100_003, 20260501, n_orders=10, gmv=500_000),
    ]
    summaries = seller_summary(rows)
    top = top_sellers_by_gmv(summaries, n=3)
    assert [s.seller_id for s in top] == [100_002, 100_001, 100_003]


def test_top_sellers_ties_broken_by_seller_id():
    rows = [
        _fact(100_002, 20260501, n_orders=10, gmv=1_000_000),
        _fact(100_001, 20260501, n_orders=10, gmv=1_000_000),
    ]
    summaries = seller_summary(rows)
    top = top_sellers_by_gmv(summaries, n=2)
    assert [s.seller_id for s in top] == [100_001, 100_002]


def test_top_sellers_validates_n():
    with pytest.raises(ValueError):
        top_sellers_by_gmv({}, n=0)


def test_worst_filters_low_order_sellers():
    rows = [
        # Seller 1: 100% return rate but only 2 orders → filtered.
        _fact(100_001, 20260501, n_orders=2, gmv=200_000, n_returns=2),
        # Seller 2: 20% return rate with 20 orders → kept.
        _fact(100_002, 20260501, n_orders=20, gmv=2_000_000, n_returns=4),
    ]
    summaries = seller_summary(rows)
    worst = worst_sellers_by_return_rate(summaries, n=10, min_orders=10)
    assert len(worst) == 1
    assert worst[0].seller_id == 100_002


def test_worst_validates():
    with pytest.raises(ValueError):
        worst_sellers_by_return_rate({}, n=0)
    with pytest.raises(ValueError):
        worst_sellers_by_return_rate({}, n=5, min_orders=-1)


def test_daily_trend_aggregates_across_sellers():
    rows = [
        _fact(100_001, 20260501, n_orders=10, gmv=1_000_000),
        _fact(100_002, 20260501, n_orders=5, gmv=500_000),
        _fact(100_001, 20260502, n_orders=8, gmv=800_000),
    ]
    trend = daily_trend(rows)
    assert [t.date_key for t in trend] == [20260501, 20260502]
    assert trend[0].n_orders == 15
    assert trend[0].gmv_vnd == 1_500_000
    assert trend[1].n_orders == 8


def test_daily_trend_return_rate_zero_for_empty_day():
    """Defensive — if a future caller hands us a zero-order DailyTrend, no div-by-zero."""
    from sellermart.kpis import DailyTrend

    d = DailyTrend(date_key=20260501, n_orders=0, n_units=0, gmv_vnd=0, n_returns=0, refund_vnd=0)
    assert d.return_rate_pct == 0.0
