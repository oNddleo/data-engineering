"""Detector tests."""

from __future__ import annotations

import pytest

from flashpipe.detectors import (
    HotnessKind,
    StampedeDetector,
    detect_burndown,
    detect_hot_product,
)
from flashpipe.windows import WindowAggregate

from ._fixtures import t_at


def _agg(
    *,
    item_id: int = 1,
    n_views: int = 0,
    n_orders: int = 0,
    units_sold: int = 0,
    window_start: int = 0,
    window_seconds: int = 1,
) -> WindowAggregate:
    return WindowAggregate(
        window_start=t_at(window_start),
        window_end=t_at(window_start + window_seconds),
        item_id=item_id,
        n_views=n_views,
        n_add_to_cart=0,
        n_checkout=0,
        n_orders=n_orders,
        units_sold=units_sold,
        gmv_vnd=0,
        unique_users=0,
    )


# ---------- hot product ----------


def test_hot_product_fires_on_views_threshold():
    out = detect_hot_product(_agg(n_views=2_000), min_views=1_000, min_orders=50)
    assert out is not None
    assert out.kind is HotnessKind.HOT_PRODUCT


def test_hot_product_fires_on_orders_threshold():
    out = detect_hot_product(_agg(n_orders=60), min_views=1_000, min_orders=50)
    assert out is not None


def test_hot_product_silent_below_both_thresholds():
    assert detect_hot_product(_agg(n_views=500, n_orders=20)) is None


def test_hot_product_carries_max_metric():
    out = detect_hot_product(_agg(n_views=200, n_orders=100), min_views=300, min_orders=50)
    assert out is not None
    assert out.metric == 200  # max(views, orders)


# ---------- stampede ----------


def test_stampede_fires_on_10x_spike():
    det = StampedeDetector(multiplier=10.0, min_baseline=10)
    det.consume(_agg(n_views=10))
    out = det.consume(_agg(n_views=100))
    assert out is not None
    assert out.kind is HotnessKind.STAMPEDE


def test_stampede_silent_below_multiplier():
    det = StampedeDetector(multiplier=10.0, min_baseline=10)
    det.consume(_agg(n_views=10))
    assert det.consume(_agg(n_views=50)) is None  # only 5×


def test_stampede_silent_when_baseline_too_low():
    det = StampedeDetector(multiplier=10.0, min_baseline=10)
    det.consume(_agg(n_views=5))
    assert det.consume(_agg(n_views=1000)) is None  # baseline below min_baseline


def test_stampede_per_item_independent():
    det = StampedeDetector(multiplier=10.0, min_baseline=10)
    det.consume(_agg(item_id=1, n_views=20))
    out = det.consume(_agg(item_id=2, n_views=1000))  # different item, no baseline
    assert out is None


def test_stampede_rejects_bad_multiplier():
    with pytest.raises(ValueError):
        StampedeDetector(multiplier=1.0)


def test_stampede_rejects_bad_min_baseline():
    with pytest.raises(ValueError):
        StampedeDetector(min_baseline=0)


# ---------- inventory burndown ----------


def test_burndown_fires_when_rate_too_high():
    """100 units sold/1s = 100 units/s; stock=100 → 1s to zero, < 60s horizon."""
    out = detect_burndown(_agg(units_sold=100, window_seconds=1), current_stock=100)
    assert out is not None
    assert out.kind is HotnessKind.INVENTORY_BURNDOWN


def test_burndown_silent_when_horizon_not_threatened():
    """1 unit sold/1s = 1 unit/s; stock=1000 → 1000s, > 60s horizon."""
    out = detect_burndown(_agg(units_sold=1, window_seconds=1), current_stock=1000)
    assert out is None


def test_burndown_silent_when_no_sales():
    out = detect_burndown(_agg(units_sold=0), current_stock=100)
    assert out is None


def test_burndown_silent_when_stock_zero():
    out = detect_burndown(_agg(units_sold=10), current_stock=0)
    assert out is None


def test_burndown_rejects_bad_horizon():
    with pytest.raises(ValueError):
        detect_burndown(_agg(units_sold=1), current_stock=10, horizon_seconds=0)
