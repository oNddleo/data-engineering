"""Watermark generator semantics across three strategies."""

from __future__ import annotations

from datetime import timedelta

from latebuf.schema import BufferConfig, WatermarkStrategy
from latebuf.watermark import new_watermark

from ._fixtures import DEFAULT_TS, event_at

# ---------- HEURISTIC --------------------------------------------------------


def test_heuristic_first_event_advances_to_event_time_minus_lateness():
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.HEURISTIC,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    advance = wm.update(event_at("E-1", 100))
    assert advance == DEFAULT_TS + timedelta(seconds=90)


def test_heuristic_monotonic():
    """Watermark only advances forward, never backward."""
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.HEURISTIC,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    wm.update(event_at("E-1", 100))  # max_et = 100, watermark = 90
    advance = wm.update(event_at("E-2", 50))  # max_et stays 100, no advance
    assert advance is None
    assert wm.get() == DEFAULT_TS + timedelta(seconds=90)


def test_heuristic_advances_with_later_event():
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.HEURISTIC,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    wm.update(event_at("E-1", 100))  # watermark = 90
    advance = wm.update(event_at("E-2", 200))  # watermark = 190
    assert advance == DEFAULT_TS + timedelta(seconds=190)


# ---------- PERIODIC ---------------------------------------------------------


def test_periodic_first_event_advances():
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.PERIODIC,
            allowed_lateness=timedelta(seconds=10),
            periodic_tick=timedelta(seconds=5),
        )
    )
    advance = wm.update(event_at("E-1", 100))
    assert advance == DEFAULT_TS + timedelta(seconds=90)


def test_periodic_does_not_advance_within_tick():
    """Within ``periodic_tick`` window, the watermark stays put even if
    max(event_time) has moved."""
    config = BufferConfig(
        strategy=WatermarkStrategy.PERIODIC,
        allowed_lateness=timedelta(seconds=10),
        periodic_tick=timedelta(seconds=5),
    )
    wm = new_watermark(config)
    # E-1: event_time=+100, ingest_time=+200 → first tick, watermark advances to 90.
    wm.update(event_at("E-1", 100, ingest_time_offset_s=200))
    # E-2: event_time=+150 (higher max), ingest_time=+201 (only +1s).
    # ingest diff 1s < tick 5s → no advance, watermark stays at 90.
    advance = wm.update(event_at("E-2", 150, ingest_time_offset_s=201))
    assert advance is None
    assert wm.get() == DEFAULT_TS + timedelta(seconds=90)


def test_periodic_advances_after_tick():
    """After ``periodic_tick`` seconds in processing-time, the watermark advances."""
    config = BufferConfig(
        strategy=WatermarkStrategy.PERIODIC,
        allowed_lateness=timedelta(seconds=10),
        periodic_tick=timedelta(seconds=5),
    )
    wm = new_watermark(config)
    # E-1: event_time=+100, ingest_time=+100 → watermark=90, last_tick=100.
    wm.update(event_at("E-1", 100, ingest_time_offset_s=100))
    # E-2: event_time=+110, ingest_time=+110 → ingest diff = 10s > 5s tick →
    # advance. Max=110, target=100.
    advance = wm.update(event_at("E-2", 110, ingest_time_offset_s=110))
    assert advance == DEFAULT_TS + timedelta(seconds=100)


# ---------- PUNCTUATED -------------------------------------------------------


def test_punctuated_no_advance_on_normal_event():
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    advance = wm.update(event_at("E-1", 100))
    assert advance is None
    assert wm.get() is None


def test_punctuated_advances_on_punctuation():
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    wm.update(event_at("E-1", 100))  # no advance
    advance = wm.update(event_at("END-1", 100, is_punctuation=True))
    assert advance == DEFAULT_TS + timedelta(seconds=90)


def test_punctuated_uses_max_event_time_at_punctuation_arrival():
    """After several normal events, a punctuation flushes the max."""
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    wm.update(event_at("E-1", 100))
    wm.update(event_at("E-2", 200))  # max_et = 200
    advance = wm.update(event_at("END-1", 100, is_punctuation=True))
    assert advance == DEFAULT_TS + timedelta(seconds=190)


# ---------- finalise ---------------------------------------------------------


def test_finalise_no_events_returns_none():
    wm = new_watermark(BufferConfig())
    assert wm.finalise() is None


def test_finalise_after_punctuated_with_no_punctuation():
    """PUNCTUATED with no punctuation: finalise() forces advance."""
    wm = new_watermark(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=10),
        )
    )
    wm.update(event_at("E-1", 100))
    out = wm.finalise()
    assert out == DEFAULT_TS + timedelta(seconds=90)
