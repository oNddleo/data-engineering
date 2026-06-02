"""Anomaly detection: zero usage, sudden drop, unrealistic spike."""

from __future__ import annotations

from datetime import date

import pytest

from evn.anomaly import (
    find_sudden_drops,
    find_unrealistic_spikes,
    find_zero_usage,
)
from evn.schema import AnomalyKind

from ._fixtures import make_reading


def _history(
    customer_code: str,
    kwh_per_month: list[int],
) -> list:
    """Build a sequential history of monthly readings."""
    out = []
    for i, kwh in enumerate(kwh_per_month):
        out.append(
            make_reading(
                customer_code=customer_code,
                period_start=date(2025, i + 1, 1),
                period_end=date(2025, i + 1, 28),
                kwh_used=kwh,
            )
        )
    return out


# ---------- Zero usage ------------------------------------------------------


def test_zero_usage_fires_on_recent_zero() -> None:
    """A zero-kWh month after a non-zero history fires."""
    readings = _history("PA00000000001", [100, 110, 120, 105, 0])
    findings = find_zero_usage(readings)
    assert len(findings) == 1
    assert findings[0].kind is AnomalyKind.ZERO_USAGE


def test_zero_usage_silent_on_active_customer() -> None:
    """No zero in recent month → no finding."""
    readings = _history("PA00000000001", [100, 110, 120, 105, 130])
    assert find_zero_usage(readings) == []


def test_zero_usage_silent_on_pure_vacancy() -> None:
    """A customer who's been zero for the trailing window is not flagged."""
    readings = _history("PA00000000001", [100, 0, 0, 0, 0])
    # Trailing 3 are zero AND latest is zero → genuine vacancy.
    assert find_zero_usage(readings) == []


def test_zero_usage_needs_baseline() -> None:
    """Need at least 3 trailing readings to establish a baseline."""
    readings = _history("PA00000000001", [100, 0])
    assert find_zero_usage(readings) == []


# ---------- Sudden drop -----------------------------------------------------


def test_sudden_drop_fires_on_steep_drop() -> None:
    """A 100→10 drop (90%) fires at the default 80% threshold."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 10])
    findings = find_sudden_drops(readings)
    assert len(findings) == 1
    assert findings[0].kind is AnomalyKind.SUDDEN_DROP


def test_sudden_drop_silent_below_threshold() -> None:
    """A 100→60 drop (40%) doesn't fire at the default threshold."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 60])
    assert find_sudden_drops(readings) == []


def test_sudden_drop_silent_on_tiny_baseline() -> None:
    """Baselines < 10 kWh are not actionable — too noisy."""
    readings = _history("PA00000000001", [5, 6, 7, 8, 1])
    assert find_sudden_drops(readings) == []


def test_sudden_drop_silent_on_zero() -> None:
    """Zero-kWh latest is the ZERO_USAGE signal's job, not SUDDEN_DROP."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 0])
    assert find_sudden_drops(readings) == []


def test_sudden_drop_custom_threshold() -> None:
    """Lowering the threshold makes smaller drops fire."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 60])
    findings = find_sudden_drops(readings, max_drop_ratio=0.30)
    assert len(findings) == 1


def test_sudden_drop_validates_threshold() -> None:
    with pytest.raises(ValueError, match="max_drop_ratio"):
        find_sudden_drops([], max_drop_ratio=0.0)
    with pytest.raises(ValueError, match="max_drop_ratio"):
        find_sudden_drops([], max_drop_ratio=1.0)


# ---------- Unrealistic spike ----------------------------------------------


def test_spike_fires_on_5x_jump() -> None:
    """A 100→600 spike (6×) fires at the default 5× threshold."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 600])
    findings = find_unrealistic_spikes(readings)
    assert len(findings) == 1
    assert findings[0].kind is AnomalyKind.UNREALISTIC_SPIKE


def test_spike_silent_below_threshold() -> None:
    """A 100→200 jump (2×) doesn't fire at default."""
    readings = _history("PA00000000001", [100, 110, 120, 100, 200])
    assert find_unrealistic_spikes(readings) == []


def test_spike_needs_baseline() -> None:
    """Too few prior readings → can't compute baseline."""
    readings = _history("PA00000000001", [10, 500])
    assert find_unrealistic_spikes(readings) == []


def test_spike_custom_multiplier() -> None:
    """Looser multiplier surfaces 3× spikes."""
    readings = _history("PA00000000001", [100, 100, 100, 100, 300])
    findings = find_unrealistic_spikes(readings, min_spike_multiplier=2.5)
    assert len(findings) == 1


def test_spike_validates_multiplier() -> None:
    with pytest.raises(ValueError, match="min_spike_multiplier"):
        find_unrealistic_spikes([], min_spike_multiplier=1.0)


def test_spike_silent_on_tiny_baseline() -> None:
    """Baselines < 10 kWh are not actionable."""
    readings = _history("PA00000000001", [5, 6, 7, 8, 100])
    assert find_unrealistic_spikes(readings) == []
