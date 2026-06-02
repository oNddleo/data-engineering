"""compute_stats over a buffer run."""

from __future__ import annotations

from datetime import timedelta

from latebuf.buffer import LateArrivingBuffer
from latebuf.metrics import compute_stats
from latebuf.schema import BufferConfig

from ._fixtures import event_at


def test_stats_no_events():
    buf = LateArrivingBuffer()
    s = compute_stats(buf)
    assert s.n_accepted == 0
    assert s.max_lateness_seconds == 0
    assert s.median_lateness_seconds == 0


def test_stats_on_time_run():
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=60)))
    for i in range(10):
        buf.accept(event_at(f"E-{i:02d}", i * 5))
    buf.flush()
    s = compute_stats(buf)
    assert s.n_dead_lettered == 0
    assert s.max_lateness_seconds == 0


def test_stats_records_lateness_percentiles():
    """Drop some events explicitly late → percentiles computed."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=5)))
    # First event sets watermark = 95
    buf.accept(event_at("E-1", 100))
    # Bump watermark to 195
    buf.accept(event_at("E-2", 200))
    # Now drop a few late events with varying lateness.
    for i, ev_offset in enumerate((50, 100, 150, 180)):
        buf.accept(event_at(f"E-late-{i}", ev_offset, ingest_time_offset_s=200))
    s = compute_stats(buf)
    assert s.n_dead_lettered == 4
    assert s.max_lateness_seconds > 0
    assert s.median_lateness_seconds > 0


def test_stats_drop_rate_pct():
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=5)))
    buf.accept(event_at("E-1", 100))
    buf.accept(event_at("E-2", 200))  # advances watermark
    # 8 late, 0 on-time → drop_rate = 8/10 = 80%
    for i in range(8):
        buf.accept(event_at(f"E-late-{i}", 50, ingest_time_offset_s=200))
    s = compute_stats(buf)
    assert s.n_accepted == 10
    assert s.n_dead_lettered == 8
    assert s.drop_rate_pct == 80.0
