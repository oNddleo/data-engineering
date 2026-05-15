"""Detector tests."""

from __future__ import annotations

import pytest

from multiprice.detectors import (
    detect_arbitrage,
    detect_below_map,
    detect_price_changes,
    detect_stockouts,
)
from multiprice.events import Direction
from multiprice.schema import Platform
from multiprice.store import ObservationStore

from ._fixtures import make_obs, t_at

# ---------- price changes ----------


def test_price_change_no_history_no_events():
    s = ObservationStore()
    s.append(make_obs(price=100_000))
    assert detect_price_changes(s) == []


def test_price_change_unchanged_no_event():
    s = ObservationStore()
    s.append(make_obs(price=100_000, observed_at=t_at(0)))
    s.append(make_obs(price=100_000, observed_at=t_at(10)))
    assert detect_price_changes(s) == []


def test_price_change_down_fires():
    s = ObservationStore()
    s.append(make_obs(price=200_000, observed_at=t_at(0)))
    s.append(make_obs(price=150_000, observed_at=t_at(10)))
    events = detect_price_changes(s)
    assert len(events) == 1
    assert events[0].direction is Direction.DOWN
    assert events[0].pct_change < 0
    assert events[0].previous_price_vnd == 200_000
    assert events[0].current_price_vnd == 150_000


def test_price_change_up_fires():
    s = ObservationStore()
    s.append(make_obs(price=100_000, observed_at=t_at(0)))
    s.append(make_obs(price=130_000, observed_at=t_at(10)))
    events = detect_price_changes(s)
    assert events[0].direction is Direction.UP
    assert events[0].pct_change > 0


def test_price_change_respects_min_pct():
    s = ObservationStore()
    s.append(make_obs(price=200_000, observed_at=t_at(0)))
    s.append(make_obs(price=195_000, observed_at=t_at(10)))  # -2.5%
    # min_pct_change=5 → suppress
    assert detect_price_changes(s, min_pct_change=5) == []
    assert len(detect_price_changes(s, min_pct_change=1)) == 1


def test_price_change_only_latest_transition():
    s = ObservationStore()
    s.append(make_obs(price=100_000, observed_at=t_at(0)))
    s.append(make_obs(price=120_000, observed_at=t_at(10)))
    s.append(make_obs(price=150_000, observed_at=t_at(20)))
    events = detect_price_changes(s)
    # Only the (120k → 150k) transition is reported.
    assert len(events) == 1
    assert events[0].previous_price_vnd == 120_000
    assert events[0].current_price_vnd == 150_000


def test_price_change_rejects_negative_min_pct():
    with pytest.raises(ValueError):
        detect_price_changes(ObservationStore(), min_pct_change=-1)


# ---------- arbitrage ----------


def test_arbitrage_one_platform_no_event():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100_000))
    assert detect_arbitrage(s) == []


def test_arbitrage_small_spread_no_event():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100_000))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", price=105_000))
    assert detect_arbitrage(s, min_spread_pct=10) == []


def test_arbitrage_large_spread_fires():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100_000))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", price=130_000))
    events = detect_arbitrage(s, min_spread_pct=10)
    assert len(events) == 1
    assert events[0].cheapest_platform is Platform.SHOPEE
    assert events[0].most_expensive_platform is Platform.LAZADA
    assert events[0].spread_vnd == 30_000


def test_arbitrage_three_platforms():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100_000))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", price=120_000))
    s.append(make_obs(platform=Platform.TIKI, platform_item_id="tk", price=150_000))
    events = detect_arbitrage(s, min_spread_pct=10)
    assert events[0].cheapest_platform is Platform.SHOPEE
    assert events[0].most_expensive_platform is Platform.TIKI


def test_arbitrage_skips_out_of_stock():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", price=100_000, stock=0))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", price=150_000, stock=10))
    # Only one platform in-stock → no arbitrage.
    assert detect_arbitrage(s) == []


def test_arbitrage_rejects_negative_min_spread():
    with pytest.raises(ValueError):
        detect_arbitrage(ObservationStore(), min_spread_pct=-1)


# ---------- stockouts ----------


def test_stockout_fires_when_stock_zero():
    s = ObservationStore()
    s.append(make_obs(stock=0))
    events = detect_stockouts(s)
    assert len(events) == 1


def test_stockout_skips_in_stock():
    s = ObservationStore()
    s.append(make_obs(stock=10))
    assert detect_stockouts(s) == []


def test_stockout_uses_latest_observation():
    """If most recent stock = 0 but earlier had stock, still alert."""
    s = ObservationStore()
    s.append(make_obs(stock=100, observed_at=t_at(0)))
    s.append(make_obs(stock=0, observed_at=t_at(60)))
    assert len(detect_stockouts(s)) == 1


def test_stockout_per_platform():
    s = ObservationStore()
    s.append(make_obs(platform=Platform.SHOPEE, platform_item_id="sp", stock=0))
    s.append(make_obs(platform=Platform.LAZADA, platform_item_id="lz", stock=10))
    s.append(make_obs(platform=Platform.TIKI, platform_item_id="tk", stock=0))
    events = detect_stockouts(s)
    platforms = {e.platform for e in events}
    assert platforms == {Platform.SHOPEE, Platform.TIKI}


# ---------- MAP breach ----------


def test_below_map_fires_when_price_below_map():
    s = ObservationStore()
    s.append(make_obs(price=80_000))
    events = detect_below_map(s, map_table={"SKU-1": 100_000})
    assert len(events) == 1
    assert events[0].breach_vnd == 20_000


def test_below_map_skips_when_price_at_map():
    s = ObservationStore()
    s.append(make_obs(price=100_000))
    assert detect_below_map(s, map_table={"SKU-1": 100_000}) == []


def test_below_map_skips_skus_without_entry():
    s = ObservationStore()
    s.append(make_obs(price=50_000))
    assert detect_below_map(s, map_table={}) == []
