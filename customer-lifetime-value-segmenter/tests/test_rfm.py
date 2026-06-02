"""RFM scoring behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from clvseg.rfm import score
from clvseg.schema import VN_TZ

from ._fixtures import DEFAULT_TS, make_customer, make_order


def test_score_single_customer_no_orders():
    """A customer with no orders gets R/F/M = 1/1/1 (LOST corner)."""
    c = make_customer(customer_id="C-1")
    scores = score([c], [], as_of=DEFAULT_TS)
    assert len(scores) == 1
    s = scores[0]
    assert s.customer_id == "C-1"
    assert s.frequency == 0
    assert s.monetary_vnd == 0
    assert s.f_score == 1
    assert s.m_score == 1


def test_score_validates_as_of_tz():
    with pytest.raises(ValueError):
        score([], [], as_of=datetime(2026, 5, 14))


def test_score_recency_relative_to_last_order():
    c = make_customer(customer_id="C-1")
    orders = [
        make_order(order_id="O-1", customer_id="C-1", placed_at=DEFAULT_TS - timedelta(days=10)),
        make_order(
            order_id="O-2", customer_id="C-1", placed_at=DEFAULT_TS - timedelta(days=3)
        ),  # most recent
    ]
    scores = score([c], orders, as_of=DEFAULT_TS)
    assert scores[0].recency_days == 3


def test_score_frequency_counts_orders():
    c = make_customer(customer_id="C-1")
    orders = [
        make_order(
            order_id=f"O-{i}", customer_id="C-1", placed_at=DEFAULT_TS - timedelta(days=i + 1)
        )
        for i in range(5)
    ]
    scores = score([c], orders, as_of=DEFAULT_TS)
    assert scores[0].frequency == 5


def test_score_monetary_sums_gross():
    c = make_customer(customer_id="C-1")
    orders = [
        make_order(order_id="O-1", customer_id="C-1", gross_vnd=300_000),
        make_order(order_id="O-2", customer_id="C-1", gross_vnd=500_000),
    ]
    scores = score([c], orders, as_of=DEFAULT_TS)
    assert scores[0].monetary_vnd == 800_000


def test_score_orphan_orders_ignored():
    """An order for an unknown customer doesn't appear in any score."""
    c = make_customer(customer_id="C-1")
    orphan = make_order(order_id="O-orphan", customer_id="GHOST")
    scores = score([c], [orphan], as_of=DEFAULT_TS)
    assert scores[0].frequency == 0


def test_score_top_recency_gets_high_r():
    """Most-recent buyer gets the highest R score."""
    customers = [make_customer(customer_id=f"C-{i}") for i in range(10)]
    orders = []
    # 10 customers, each with one order 10..1 days ago.
    for i in range(10):
        orders.append(
            make_order(
                order_id=f"O-{i}",
                customer_id=f"C-{i}",
                placed_at=DEFAULT_TS - timedelta(days=10 - i),
            )
        )
    scores = score(customers, orders, as_of=DEFAULT_TS)
    # C-9 bought yesterday → highest R.
    by_id = {s.customer_id: s for s in scores}
    assert by_id["C-9"].r_score == 5  # top quintile recency
    assert by_id["C-0"].r_score == 1  # bottom quintile


def test_score_top_frequency_gets_high_f():
    customers = [make_customer(customer_id=f"C-{i}") for i in range(5)]
    orders = []
    for i in range(5):
        # C-i gets (i + 1) orders.
        for j in range(i + 1):
            orders.append(
                make_order(
                    order_id=f"O-{i}-{j}",
                    customer_id=f"C-{i}",
                    placed_at=DEFAULT_TS - timedelta(days=j + 1),
                )
            )
    scores = score(customers, orders, as_of=DEFAULT_TS)
    by_id = {s.customer_id: s for s in scores}
    assert by_id["C-4"].f_score == 5
    assert by_id["C-0"].f_score == 1


def test_score_stable_output_order():
    customers = [
        make_customer(customer_id="C-A"),
        make_customer(customer_id="C-B"),
        make_customer(customer_id="C-C"),
    ]
    scores = score(customers, [], as_of=DEFAULT_TS)
    assert [s.customer_id for s in scores] == ["C-A", "C-B", "C-C"]


def test_score_handles_utc_as_of():
    """A UTC as_of still produces correct recency days."""
    from datetime import timezone

    c = make_customer(customer_id="C-1", registered_at=datetime(2025, 5, 14, tzinfo=VN_TZ))
    utc_as_of = datetime(2026, 5, 14, 2, 0, tzinfo=timezone.utc)  # = 09:00 VN
    scores = score([c], [], as_of=utc_as_of)
    assert scores[0].recency_days >= 365
