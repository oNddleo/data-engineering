"""ETL roll-up behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sellermart.etl import build_fact_seller_day
from sellermart.schema import VN_TZ, make_date_key

from ._fixtures import DEFAULT_TS, make_order, make_return, make_review


def test_single_order_produces_one_fact():
    facts = build_fact_seller_day([make_order()], [], [])
    assert len(facts) == 1
    f = facts[0]
    assert f.seller_id == 100_001
    assert f.date_key == make_date_key(DEFAULT_TS.date())
    assert f.n_orders == 1
    assert f.n_units == 2
    assert f.gmv_vnd == 999_000
    assert f.n_returns == 0
    assert f.n_reviews == 0
    assert f.n_unique_buyers == 1


def test_orders_share_bucket_by_seller_and_day():
    o1 = make_order(order_id="O-1", buyer_id="B-1")
    o2 = make_order(
        order_id="O-2",
        buyer_id="B-2",
        gross_vnd=500_000,
        n_units=1,
        created_at=DEFAULT_TS + timedelta(hours=1),
    )
    facts = build_fact_seller_day([o1, o2], [], [])
    assert len(facts) == 1
    f = facts[0]
    assert f.n_orders == 2
    assert f.n_units == 3
    assert f.gmv_vnd == 1_499_000
    assert f.n_unique_buyers == 2


def test_returns_credited_to_order_day():
    o = make_order(created_at=DEFAULT_TS)
    # Return processed 3 days later — still credited to the order's day.
    r = make_return(created_at=DEFAULT_TS + timedelta(days=3), refund_vnd=300_000)
    facts = build_fact_seller_day([o], [r], [])
    assert len(facts) == 1
    assert facts[0].n_returns == 1
    assert facts[0].refund_vnd == 300_000


def test_orphan_returns_are_dropped():
    """A return whose order isn't in the input is silently dropped — it will be replayed."""
    r = make_return(order_id="O-NOT-PRESENT")
    facts = build_fact_seller_day([], [r], [])
    assert facts == []


def test_reviews_bucket_on_review_day_not_order_day():
    o = make_order(created_at=DEFAULT_TS)
    rv = make_review(created_at=DEFAULT_TS + timedelta(days=2), rating_x100=400)
    facts = build_fact_seller_day([o], [], [rv])
    # Two rows: one for the order day, one for the review day with no orders →
    # but the review-only day is dropped because the grain demands an order.
    assert len(facts) == 1
    f = facts[0]
    assert f.n_reviews == 0  # the review went to a different day, which got dropped


def test_review_same_day_aggregates():
    o = make_order(created_at=DEFAULT_TS)
    rv1 = make_review(review_id="RV-1", rating_x100=500, created_at=DEFAULT_TS)
    rv2 = make_review(review_id="RV-2", rating_x100=400, created_at=DEFAULT_TS)
    facts = build_fact_seller_day([o], [], [rv1, rv2])
    assert facts[0].n_reviews == 2
    assert facts[0].sum_rating_x100 == 900


def test_vn_timezone_bucketing():
    """Order at 23:30 UTC on day D is 06:30 VN on day D+1 — bucket on the VN day."""
    utc_late = datetime(2026, 5, 14, 23, 30, 0, tzinfo=timezone.utc)
    # Same instant in VN_TZ is 2026-05-15 06:30 → date_key 20260515.
    o = make_order(created_at=utc_late)
    facts = build_fact_seller_day([o], [], [])
    assert facts[0].date_key == 20260515


def test_different_days_split_into_two_rows():
    o1 = make_order(order_id="O-1", created_at=DEFAULT_TS)
    o2 = make_order(order_id="O-2", created_at=DEFAULT_TS + timedelta(days=1))
    facts = build_fact_seller_day([o1, o2], [], [])
    assert len(facts) == 2
    assert facts[0].date_key < facts[1].date_key


def test_facts_are_sorted_by_seller_then_date():
    o1 = make_order(order_id="O-1", seller_id=100_002, created_at=DEFAULT_TS)
    o2 = make_order(order_id="O-2", seller_id=100_001, created_at=DEFAULT_TS + timedelta(days=1))
    o3 = make_order(order_id="O-3", seller_id=100_001, created_at=DEFAULT_TS)
    facts = build_fact_seller_day([o1, o2, o3], [], [])
    keys = [(f.seller_id, f.date_key) for f in facts]
    assert keys == sorted(keys)


def test_same_buyer_twice_counts_once_in_unique_buyers():
    o1 = make_order(order_id="O-1", buyer_id="B-1")
    o2 = make_order(order_id="O-2", buyer_id="B-1")
    facts = build_fact_seller_day([o1, o2], [], [])
    assert facts[0].n_unique_buyers == 1
    assert facts[0].n_orders == 2


def test_review_only_day_with_no_order_drops_bucket():
    """Pure-review day (no orders) must not produce a fact row — invariant on grain."""
    rv = make_review(created_at=DEFAULT_TS + timedelta(days=5))
    facts = build_fact_seller_day([], [], [rv])
    assert facts == []


def test_vn_tz_already_local_unchanged():
    """VN-local timestamp keeps its date even after conversion."""
    local = datetime(2026, 5, 14, 23, 59, 0, tzinfo=VN_TZ)
    o = make_order(created_at=local)
    facts = build_fact_seller_day([o], [], [])
    assert facts[0].date_key == 20260514
