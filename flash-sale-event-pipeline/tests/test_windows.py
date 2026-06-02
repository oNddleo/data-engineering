"""TumblingAggregator tests."""

from __future__ import annotations

import pytest

from flashpipe.events import EventKind
from flashpipe.windows import TumblingAggregator, window_start_for

from ._fixtures import make_event, t_at


def test_window_start_for_aligns_to_second():
    ws = window_start_for(t_at(3.7), window_seconds=1)
    assert ws == t_at(3)


def test_window_start_for_5_second_bucket():
    ws = window_start_for(t_at(13), window_seconds=5)
    assert ws == t_at(10)


def test_aggregator_rejects_zero_window():
    with pytest.raises(ValueError):
        TumblingAggregator(window_seconds=0)


def test_consume_one_view_no_close_without_watermark():
    agg = TumblingAggregator(window_seconds=1)
    closed = agg.consume(make_event(created_at=t_at(0.5)), watermark=None)
    assert closed == []
    assert agg.n_open_windows == 1


def test_consume_closes_window_when_watermark_passes():
    agg = TumblingAggregator(window_seconds=1)
    agg.consume(make_event(event_id="E1", created_at=t_at(0.2)), watermark=None)
    closed = agg.consume(make_event(event_id="E2", created_at=t_at(5)), watermark=t_at(5))
    # Window [0, 1) is now closed.
    assert len(closed) == 1
    assert closed[0].window_start == t_at(0)
    assert closed[0].n_views == 1


def test_window_aggregates_all_kinds():
    agg = TumblingAggregator(window_seconds=10)
    agg.consume(make_event(event_id="V", kind=EventKind.VIEW, created_at=t_at(0)), watermark=None)
    agg.consume(
        make_event(event_id="AC", kind=EventKind.ADD_TO_CART, created_at=t_at(1)),
        watermark=None,
    )
    agg.consume(
        make_event(event_id="CO", kind=EventKind.CHECKOUT, created_at=t_at(2)),
        watermark=None,
    )
    agg.consume(
        make_event(
            event_id="O",
            kind=EventKind.ORDER,
            quantity=3,
            amount_vnd=300_000,
            created_at=t_at(3),
        ),
        watermark=None,
    )
    closed = agg.flush_all()
    assert len(closed) == 1
    a = closed[0]
    assert a.n_views == 1
    assert a.n_add_to_cart == 1
    assert a.n_checkout == 1
    assert a.n_orders == 1
    assert a.units_sold == 3
    assert a.gmv_vnd == 300_000


def test_window_tracks_unique_users():
    agg = TumblingAggregator(window_seconds=10)
    for i in range(5):
        agg.consume(
            make_event(event_id=f"V-{i}", user_id=f"U-{i % 3}", created_at=t_at(0)),
            watermark=None,
        )
    closed = agg.flush_all()
    assert closed[0].unique_users == 3  # U-0, U-1, U-2


def test_window_conversion_pct():
    agg = TumblingAggregator(window_seconds=10)
    for i in range(10):
        agg.consume(
            make_event(event_id=f"V-{i}", user_id=f"U-{i}", created_at=t_at(0)),
            watermark=None,
        )
    agg.consume(
        make_event(
            event_id="O",
            kind=EventKind.ORDER,
            user_id="U-buyer",
            quantity=1,
            amount_vnd=100_000,
            created_at=t_at(0),
        ),
        watermark=None,
    )
    closed = agg.flush_all()
    assert closed[0].conversion_pct == 10.0  # 1 / 10 * 100


def test_late_event_dropped_from_aggregator():
    agg = TumblingAggregator(window_seconds=1)
    agg.consume(make_event(event_id="E1", created_at=t_at(10)), watermark=None)
    # An event well before the watermark — caller passes the wm:
    closed = agg.consume(make_event(event_id="E2", created_at=t_at(0)), watermark=t_at(9))
    assert agg.dropped_late_events == 1
    assert closed == []


def test_per_item_separation():
    agg = TumblingAggregator(window_seconds=10)
    agg.consume(make_event(event_id="A", item_id=1, created_at=t_at(0)), watermark=None)
    agg.consume(make_event(event_id="B", item_id=2, created_at=t_at(0)), watermark=None)
    closed = agg.flush_all()
    item_ids = {a.item_id for a in closed}
    assert item_ids == {1, 2}


def test_aggregate_immutable():
    """WindowAggregate is frozen, can't be mutated."""
    agg = TumblingAggregator(window_seconds=10)
    agg.consume(make_event(event_id="A", created_at=t_at(0)), watermark=None)
    closed = agg.flush_all()
    with pytest.raises((AttributeError, TypeError)):
        closed[0].n_views = 999  # type: ignore[misc]
