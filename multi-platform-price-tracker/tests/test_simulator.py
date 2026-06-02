"""Simulator + integration tests."""

from __future__ import annotations

from multiprice.detectors import detect_arbitrage, detect_price_changes, detect_stockouts
from multiprice.schema import Platform
from multiprice.simulator import generate
from multiprice.store import ObservationStore


def _build_store(observations):
    s = ObservationStore()
    for o in observations:
        s.append(o)
    return s


def test_generate_reproducible_with_seed():
    m1, o1 = generate(seed=42)
    m2, o2 = generate(seed=42)
    assert [m.canonical_sku for m in m1] == [m.canonical_sku for m in m2]
    assert [o.price_vnd for o in o1] == [o.price_vnd for o in o2]


def test_generate_total_counts():
    """n_skus × 3 platforms × n_snapshots."""
    _, obs = generate(seed=0, n_skus=10, n_snapshots=4)
    assert len(obs) == 10 * 3 * 4


def test_generate_mapping_per_sku_per_platform():
    mappings, _ = generate(seed=0, n_skus=10)
    assert len(mappings) == 10 * 3


def test_generate_distinct_item_ids_per_platform():
    mappings, _ = generate(seed=0, n_skus=10)
    shopee_ids = {m.platform_item_id for m in mappings if m.platform is Platform.SHOPEE}
    lazada_ids = {m.platform_item_id for m in mappings if m.platform is Platform.LAZADA}
    assert len(shopee_ids) == 10
    assert len(lazada_ids) == 10


def test_arbitrage_injection_fires_arbitrage_detector():
    _, obs = generate(seed=0, n_skus=5, n_snapshots=2, arbitrage_skus=2)
    s = _build_store(obs)
    events = detect_arbitrage(s, min_spread_pct=20)
    assert len(events) >= 2


def test_stockout_injection_fires_stockout_detector():
    _, obs = generate(seed=0, n_skus=5, n_snapshots=2, stockout_skus=2)
    s = _build_store(obs)
    events = detect_stockouts(s)
    assert len(events) >= 2


def test_baseline_produces_some_price_changes():
    """Simulator's per-snapshot price drops should produce *some* changes."""
    _, obs = generate(seed=0, n_skus=5, n_snapshots=4)
    s = _build_store(obs)
    events = detect_price_changes(s, min_pct_change=0)
    # Most series should have at least *some* difference between last two snapshots.
    # We don't assert a specific count — just non-empty.
    assert len(events) >= 1
