"""Anomaly detection: band breaches, volume spikes, price gaps."""

from __future__ import annotations

from datetime import date

import pytest

from vnstock.anomaly import (
    find_band_breaches,
    find_price_gaps,
    find_volume_spikes,
)
from vnstock.schema import AnomalyKind, Exchange

from ._fixtures import make_bar

# ---------- Band breaches --------------------------------------------------


def test_band_breach_high_above_ceiling() -> None:
    """A bar whose high > ceiling should fire."""
    # HOSE band ±7% on 50,000 → ceiling 53,500.
    bar = make_bar(
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=55_000,
        low_vnd=50_000,
        close_vnd=54_000,
    )
    out = find_band_breaches([bar])
    assert len(out) == 1
    assert out[0].kind is AnomalyKind.PRICE_BAND_BREACH


def test_band_breach_low_below_floor() -> None:
    """A bar whose low < floor should fire."""
    # HOSE band ±7% on 50,000 → floor 46,500.
    bar = make_bar(
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=50_000,
        low_vnd=45_000,
        close_vnd=46_000,
    )
    out = find_band_breaches([bar])
    assert len(out) == 1


def test_band_breach_silent_within_band() -> None:
    """A bar fully inside the band should not fire."""
    bar = make_bar(
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=53_000,
        low_vnd=48_000,
        close_vnd=52_000,
    )
    assert find_band_breaches([bar]) == []


def test_band_breach_upcom_wider_tolerance() -> None:
    """A 12% move on UPCoM (band 15%) doesn't breach; on HOSE (7%) it does."""
    hose_bar = make_bar(
        exchange=Exchange.HOSE,
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=56_000,
        low_vnd=50_000,
        close_vnd=55_000,
    )
    assert len(find_band_breaches([hose_bar])) == 1

    upcom_bar = make_bar(
        exchange=Exchange.UPCOM,
        reference_price_vnd=50_000,
        open_vnd=50_000,
        high_vnd=56_000,
        low_vnd=50_000,
        close_vnd=55_000,
    )
    assert find_band_breaches([upcom_bar]) == []


# ---------- Volume spikes --------------------------------------------------


def test_volume_spike_fires_on_10x() -> None:
    """5 stable days followed by 10× volume should fire."""
    bars = [make_bar(date=date(2025, 1, 6 + i), volume=1_000_000) for i in range(5)]
    bars.append(make_bar(date=date(2025, 1, 11), volume=10_000_000))
    out = find_volume_spikes(bars)
    assert len(out) == 1
    assert out[0].kind is AnomalyKind.VOLUME_SPIKE
    assert out[0].metric == 10


def test_volume_spike_silent_normal_pattern() -> None:
    """6 days of identical volume — no spike."""
    bars = [make_bar(date=date(2025, 1, 6 + i), volume=1_000_000) for i in range(6)]
    assert find_volume_spikes(bars) == []


def test_volume_spike_needs_history() -> None:
    """With only 3 bars (default window=5) we can't establish a baseline."""
    bars = [
        make_bar(date=date(2025, 1, 6), volume=100_000),
        make_bar(date=date(2025, 1, 7), volume=100_000),
        make_bar(date=date(2025, 1, 8), volume=2_000_000),
    ]
    assert find_volume_spikes(bars) == []


def test_volume_spike_custom_multiplier() -> None:
    """Loosen to 2× → captures smaller anomalies."""
    bars = [make_bar(date=date(2025, 1, 6 + i), volume=1_000_000) for i in range(5)]
    bars.append(make_bar(date=date(2025, 1, 11), volume=3_000_000))
    out = find_volume_spikes(bars, multiplier=2.5)
    assert len(out) == 1


def test_volume_spike_validates_multiplier() -> None:
    with pytest.raises(ValueError, match="multiplier"):
        find_volume_spikes([], multiplier=1.0)


def test_volume_spike_validates_window() -> None:
    with pytest.raises(ValueError, match="window"):
        find_volume_spikes([], window=0)


# ---------- Price gaps -----------------------------------------------------


def test_price_gap_fires_on_5_percent() -> None:
    bars = [
        make_bar(date=date(2025, 1, 6), close_vnd=60_000),
        make_bar(
            date=date(2025, 1, 7),
            open_vnd=63_500,
            high_vnd=63_700,
            low_vnd=63_300,
            close_vnd=63_500,
            reference_price_vnd=60_000,
        ),
    ]
    out = find_price_gaps(bars)
    assert len(out) == 1
    assert out[0].kind is AnomalyKind.PRICE_GAP


def test_price_gap_silent_below_threshold() -> None:
    """A 1% gap doesn't fire at default 5% threshold."""
    bars = [
        make_bar(date=date(2025, 1, 6), close_vnd=60_000),
        make_bar(
            date=date(2025, 1, 7),
            open_vnd=60_500,
            high_vnd=60_500,
            low_vnd=60_000,
            close_vnd=60_000,
            reference_price_vnd=60_000,
        ),
    ]
    assert find_price_gaps(bars) == []


def test_price_gap_custom_threshold() -> None:
    """Tighten to 50 bps (0.5%) to capture small gaps."""
    bars = [
        make_bar(date=date(2025, 1, 6), close_vnd=60_000),
        make_bar(
            date=date(2025, 1, 7),
            open_vnd=60_500,
            high_vnd=60_500,
            low_vnd=60_000,
            close_vnd=60_000,
            reference_price_vnd=60_000,
        ),
    ]
    out = find_price_gaps(bars, min_gap_bps=50)
    assert len(out) == 1


def test_price_gap_validates_threshold() -> None:
    with pytest.raises(ValueError, match="min_gap_bps"):
        find_price_gaps([], min_gap_bps=0)
