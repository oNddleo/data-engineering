"""Benchmark + dumping-risk."""

from __future__ import annotations

import pytest

from vnfishery.benchmark import (
    DUMPING_THRESHOLD_PCT,
    benchmark_usd_cents_per_kg,
    is_dumping_risk,
)
from vnfishery.schema import Grade, Market, Species


def test_known_cell_returns_price() -> None:
    p = benchmark_usd_cents_per_kg(Species.PANGASIUS, Market.US, Grade.A)
    assert p is not None and p > 0


def test_unknown_cell_returns_none() -> None:
    assert benchmark_usd_cents_per_kg(Species.OTHER, Market.US, Grade.C) is None


def test_premium_market_costs_more() -> None:
    """Black tiger to Japan should be > Black tiger to US."""
    jp = benchmark_usd_cents_per_kg(Species.BLACK_TIGER, Market.JP, Grade.A)
    us = benchmark_usd_cents_per_kg(Species.BLACK_TIGER, Market.US, Grade.A)
    assert jp is not None and us is not None
    assert jp > us


def test_grade_a_more_than_grade_b() -> None:
    a = benchmark_usd_cents_per_kg(Species.PANGASIUS, Market.US, Grade.A)
    b = benchmark_usd_cents_per_kg(Species.PANGASIUS, Market.US, Grade.B)
    assert a is not None and b is not None
    assert a > b


def test_dumping_far_below_flagged() -> None:
    """A price 60% below benchmark must be flagged."""
    bench = benchmark_usd_cents_per_kg(Species.PANGASIUS, Market.US, Grade.A)
    assert bench is not None
    assert is_dumping_risk(
        Species.PANGASIUS, Market.US, Grade.A, quoted_price_usd_cents_per_kg=bench // 3
    )


def test_dumping_at_benchmark_not_flagged() -> None:
    bench = benchmark_usd_cents_per_kg(Species.PANGASIUS, Market.US, Grade.A)
    assert bench is not None
    assert not is_dumping_risk(
        Species.PANGASIUS, Market.US, Grade.A, quoted_price_usd_cents_per_kg=bench
    )


def test_dumping_unknown_cell_not_flagged() -> None:
    """No benchmark = no judgment call."""
    assert not is_dumping_risk(
        Species.OTHER, Market.OTHER, Grade.C, quoted_price_usd_cents_per_kg=1
    )


def test_default_threshold() -> None:
    assert 0.0 < DUMPING_THRESHOLD_PCT < 1.0


@pytest.mark.parametrize("bad", [-0.1, 0.0, 1.0, 1.5])
def test_threshold_validation(bad: float) -> None:
    with pytest.raises(ValueError):
        is_dumping_risk(
            Species.PANGASIUS,
            Market.US,
            Grade.A,
            quoted_price_usd_cents_per_kg=100,
            threshold_pct=bad,
        )
