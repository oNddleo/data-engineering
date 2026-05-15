"""Anomaly detection + index calculation."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vntick.anomaly import AnomalyKind, find_circuit_breaker_hits, find_unusual_volume
from vntick.index import compute_index, hnx_index, vn30_index, vn_index
from vntick.schema import Exchange

from ._fixtures import DEFAULT_TS, make_bar, make_symbol


def test_ceiling_hit_detected():
    # VCB prev close 100_000; HOSE ±7% → ceiling = 107_000.
    bar = make_bar(
        code="VCB", high_vnd=107_000, low_vnd=105_000, open_vnd=105_000, close_vnd=107_000
    )
    hits = find_circuit_breaker_hits([bar], {"VCB": 100_000}, {"VCB": Exchange.HOSE})
    assert len(hits) == 1
    assert hits[0].kind is AnomalyKind.CEILING_HIT
    assert hits[0].metric == 107_000


def test_floor_hit_detected():
    bar = make_bar(code="VCB", high_vnd=95_000, low_vnd=93_000, open_vnd=95_000, close_vnd=93_000)
    hits = find_circuit_breaker_hits([bar], {"VCB": 100_000}, {"VCB": Exchange.HOSE})
    assert len(hits) == 1
    assert hits[0].kind is AnomalyKind.FLOOR_HIT


def test_no_hit_inside_band():
    bar = make_bar(
        code="VCB", high_vnd=105_000, low_vnd=96_000, open_vnd=100_000, close_vnd=104_000
    )
    hits = find_circuit_breaker_hits([bar], {"VCB": 100_000}, {"VCB": Exchange.HOSE})
    assert hits == []


def test_hnx_wider_band():
    """HNX is ±10%, so 109_000 is still inside the band for prev=100_000."""
    bar = make_bar(
        code="ACB", high_vnd=109_000, low_vnd=100_000, open_vnd=100_000, close_vnd=109_000
    )
    hits = find_circuit_breaker_hits([bar], {"ACB": 100_000}, {"ACB": Exchange.HNX})
    assert hits == []


def test_missing_reference_skips_symbol():
    """A symbol without prev close or exchange ref is silently skipped."""
    bar = make_bar(code="UNKNOWN", high_vnd=107_000)
    assert find_circuit_breaker_hits([bar], {}, {}) == []


def test_unusual_volume_three_sigma():
    history = [1_000_000] * 30  # zero variance
    # Spike well above mean — but std is 0 so we skip (no division).
    today = {"VCB": 5_000_000}
    assert find_unusual_volume(today, {"VCB": history}, sigma=3.0) == []


def test_unusual_volume_with_real_variance():
    history = [1_000_000, 1_200_000, 900_000, 1_100_000, 1_050_000, 950_000]
    # mean ~ 1.033M, std ~ 100K. Today = 1.5M ⇒ z ~ 4.6.
    today = {"VCB": 1_500_000}
    hits = find_unusual_volume(today, {"VCB": history}, sigma=3.0)
    assert len(hits) == 1
    assert hits[0].kind is AnomalyKind.UNUSUAL_VOLUME


def test_unusual_volume_below_threshold():
    history = [1_000_000, 1_200_000, 900_000, 1_100_000, 1_050_000, 950_000]
    today = {"VCB": 1_100_000}
    assert find_unusual_volume(today, {"VCB": history}, sigma=3.0) == []


def test_unusual_volume_short_history_skipped():
    today = {"VCB": 10_000_000}
    assert find_unusual_volume(today, {"VCB": [1_000_000, 1_000_000]}) == []


def test_unusual_volume_validates_sigma():
    with pytest.raises(ValueError):
        find_unusual_volume({}, {}, sigma=0)


def test_circuit_breaker_multiple_symbols():
    """Two symbols hitting ceiling produce two breaches."""
    bar1 = make_bar(
        code="VCB",
        bar_start=DEFAULT_TS + timedelta(minutes=5),
        high_vnd=107_000,
        low_vnd=105_000,
        open_vnd=105_000,
        close_vnd=107_000,
    )
    # VIC prev close 40_000, HOSE ceiling = 42_800; force the high there.
    bar2 = make_bar(
        code="VIC",
        bar_start=DEFAULT_TS,
        high_vnd=42_800,
        low_vnd=42_000,
        open_vnd=42_000,
        close_vnd=42_800,
    )
    hits = find_circuit_breaker_hits(
        [bar1, bar2],
        {"VCB": 100_000, "VIC": 40_000},
        {"VCB": Exchange.HOSE, "VIC": Exchange.HOSE},
    )
    assert {h.code for h in hits} == {"VCB", "VIC"}


def test_compute_index_sum_of_market_cap():
    symbols = {
        "A": make_symbol(code="A", listed_shares=1_000_000),
        "B": make_symbol(code="B", listed_shares=2_000_000),
    }
    prices = {"A": 100, "B": 200}
    # Σ = 100 × 1M + 200 × 2M = 100M + 400M = 500M.
    result = compute_index(prices, symbols, {"A", "B"})
    assert result == 500_000_000


def test_compute_index_divisor():
    symbols = {"A": make_symbol(code="A", listed_shares=1_000_000)}
    prices = {"A": 100}
    result = compute_index(prices, symbols, {"A"}, base_divisor=1_000_000)
    assert result == 100.0  # (100 × 1M) / 1M


def test_compute_index_validates_divisor():
    with pytest.raises(ValueError):
        compute_index({}, {}, set(), base_divisor=0)


def test_compute_index_halted_symbol_skipped():
    """A symbol in the universe but without a price contributes 0."""
    symbols = {
        "A": make_symbol(code="A", listed_shares=1_000_000),
        "B": make_symbol(code="B", listed_shares=1_000_000),
    }
    prices = {"A": 100}  # B halted
    result = compute_index(prices, symbols, {"A", "B"})
    assert result == 100_000_000


def test_vn_index_filters_hose():
    symbols = {
        "VCB": make_symbol(code="VCB", exchange=Exchange.HOSE, listed_shares=1_000_000),
        "ACB": make_symbol(code="ACB", exchange=Exchange.HNX, listed_shares=1_000_000),
    }
    prices = {"VCB": 100, "ACB": 50}
    # VN-Index only includes HOSE.
    assert vn_index(prices, symbols) == 100_000_000


def test_hnx_index_filters_hnx():
    symbols = {
        "VCB": make_symbol(code="VCB", exchange=Exchange.HOSE, listed_shares=1_000_000),
        "ACB": make_symbol(code="ACB", exchange=Exchange.HNX, listed_shares=1_000_000),
    }
    prices = {"VCB": 100, "ACB": 50}
    assert hnx_index(prices, symbols) == 50_000_000


def test_vn30_index_requires_non_empty():
    with pytest.raises(ValueError):
        vn30_index({}, {}, set())
