"""Tests for the backpressure monitor."""

from __future__ import annotations

from microbatch.backpressure import BackpressureMonitor


def test_no_signals_returns_zero() -> None:
    bp = BackpressureMonitor()
    assert bp.current_level() == 0.0


def test_single_signal_reflected() -> None:
    bp = BackpressureMonitor()
    bp.push("worker-1", 0.7)
    assert 0.6 < bp.current_level() < 0.8


def test_clamped_above_one() -> None:
    bp = BackpressureMonitor()
    bp.push("w", 1.5)
    assert bp.current_level() <= 1.0


def test_clamped_below_zero() -> None:
    bp = BackpressureMonitor()
    bp.push("w", -0.3)
    assert bp.current_level() >= 0.0


def test_is_saturated() -> None:
    bp = BackpressureMonitor()
    bp.push("w", 0.95)
    assert bp.is_saturated(threshold=0.85)
    assert not bp.is_saturated(threshold=0.99)


def test_multiple_sources_averaged() -> None:
    bp = BackpressureMonitor()
    bp.push("a", 0.2)
    bp.push("b", 0.8)
    level = bp.current_level()
    assert 0.2 < level < 0.8


def test_callback_fires_on_push() -> None:
    bp = BackpressureMonitor()
    received: list[float] = []
    bp.on_pressure_change(received.append)
    bp.push("w", 0.5)
    assert len(received) == 1
    assert 0.4 < received[0] < 0.6


def test_clear_resets_to_zero() -> None:
    bp = BackpressureMonitor()
    bp.push("w", 0.9)
    bp.clear()
    assert bp.current_level() == 0.0
