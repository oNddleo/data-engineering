"""Event / BufferConfig / BufferStats validation."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from latebuf.schema import (
    BufferConfig,
    BufferStats,
    EventDisposition,
    WatermarkStrategy,
)

from ._fixtures import DEFAULT_TS, make_event


def test_event_basic_ok():
    e = make_event()
    assert e.event_id == "E-0001"
    assert e.is_punctuation is False


def test_event_rejects_empty_id():
    with pytest.raises(ValueError, match="event_id"):
        make_event(event_id="")


def test_event_rejects_naive_event_time():
    with pytest.raises(ValueError, match="event_time must be timezone-aware"):
        make_event(event_time=datetime(2026, 5, 18, 9, 0, 0))


def test_event_rejects_naive_ingest_time():
    with pytest.raises(ValueError, match="ingest_time must be timezone-aware"):
        make_event(ingest_time=datetime(2026, 5, 18, 9, 0, 0))


def test_event_rejects_ingest_before_event():
    with pytest.raises(ValueError, match="before event_time"):
        make_event(
            event_time=DEFAULT_TS,
            ingest_time=DEFAULT_TS - timedelta(seconds=1),
        )


def test_event_punctuation_flag():
    e = make_event(is_punctuation=True)
    assert e.is_punctuation is True


# ---------- BufferConfig ------------------------------------------------------


def test_buffer_config_defaults():
    c = BufferConfig()
    assert c.strategy is WatermarkStrategy.HEURISTIC
    assert c.allowed_lateness == timedelta(seconds=60)


def test_buffer_config_rejects_negative_lateness():
    with pytest.raises(ValueError, match="allowed_lateness"):
        BufferConfig(allowed_lateness=timedelta(seconds=-1))


def test_buffer_config_rejects_zero_tick_for_periodic():
    with pytest.raises(ValueError, match="periodic_tick"):
        BufferConfig(
            strategy=WatermarkStrategy.PERIODIC,
            periodic_tick=timedelta(0),
        )


def test_buffer_config_allows_zero_tick_for_heuristic():
    """tick value isn't validated when strategy != PERIODIC."""
    c = BufferConfig(
        strategy=WatermarkStrategy.HEURISTIC,
        periodic_tick=timedelta(0),
    )
    assert c.strategy is WatermarkStrategy.HEURISTIC


# ---------- BufferStats -------------------------------------------------------


def test_buffer_stats_drop_rate_zero_accepted():
    s = BufferStats(
        n_accepted=0,
        n_emitted=0,
        n_dead_lettered=0,
        n_still_buffered=0,
        max_lateness_seconds=0,
        median_lateness_seconds=0,
        p99_lateness_seconds=0,
    )
    assert s.drop_rate_pct == 0.0
    assert s.total == 0


def test_buffer_stats_drop_rate_computed():
    s = BufferStats(
        n_accepted=100,
        n_emitted=90,
        n_dead_lettered=10,
        n_still_buffered=0,
        max_lateness_seconds=15,
        median_lateness_seconds=7,
        p99_lateness_seconds=14,
    )
    assert s.drop_rate_pct == 10.0
    assert s.total == 100


# ---------- Enum coverage -----------------------------------------------------


def test_event_disposition_three_values():
    assert {v.value for v in EventDisposition} == {
        "EMITTED",
        "BUFFERED",
        "DEAD_LETTERED",
    }


def test_watermark_strategy_three_values():
    assert {v.value for v in WatermarkStrategy} == {
        "HEURISTIC",
        "PERIODIC",
        "PUNCTUATED",
    }
