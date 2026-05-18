"""LateArrivingBuffer — accept + emit + dead-letter semantics."""

from __future__ import annotations

from datetime import timedelta

from latebuf.buffer import LateArrivingBuffer
from latebuf.schema import BufferConfig, EventDisposition, WatermarkStrategy

from ._fixtures import event_at


def test_buffer_empty_accept_first_event_buffers():
    """First event in: heap holds it, watermark advances."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    out = buf.accept(event_at("E-1", 100))
    # Watermark advances to 90 → E-1 (event_time=100) is NOT yet drainable.
    # So no emit yet.
    assert buf.n_buffered == 1
    assert all(r.disposition is EventDisposition.EMITTED for r in out) or not out


def test_buffer_in_order_events_emitted_after_lateness_passes():
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    buf.accept(event_at("E-1", 100))  # wm=90
    out = buf.accept(event_at("E-2", 200))  # wm=190 → drain E-1
    emitted_ids = [r.event.event_id for r in out if r.disposition is EventDisposition.EMITTED]
    assert "E-1" in emitted_ids


def test_buffer_dead_letters_late_arrival():
    """An event arriving with event_time < current watermark is dead-lettered."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    # Establish watermark = 90s
    buf.accept(event_at("E-1", 100))
    # Now bump watermark with a much later event
    buf.accept(event_at("E-2", 200))  # wm=190 after this
    # Send a late event with event_time = 50s (< watermark of 190)
    out = buf.accept(event_at("E-LATE", 50, ingest_time_offset_s=200))
    [late_record] = [r for r in out if r.event.event_id == "E-LATE"]
    assert late_record.disposition is EventDisposition.DEAD_LETTERED
    assert late_record.lateness_seconds > 0
    assert buf.n_dead_lettered == 1


def test_buffer_emits_in_event_time_order():
    """Out-of-order arrivals are reordered to event-time order on emit.

    Use a generous allowed_lateness so all three pass the late-check
    at accept-time; this test is about emit ordering, not late detection.
    """
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=60)))
    buf.accept(event_at("E-3", 30))  # arrives first
    buf.accept(event_at("E-1", 10))
    buf.accept(event_at("E-2", 20))
    final = buf.flush()
    emitted_ids = [r.event.event_id for r in final if r.disposition is EventDisposition.EMITTED]
    assert emitted_ids == ["E-1", "E-2", "E-3"]


def test_buffer_dedup_duplicate_ids():
    """Duplicate event_id is dropped silently (idempotency)."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    buf.accept(event_at("E-1", 100))
    buf.accept(event_at("E-1", 100))  # same id → dropped
    assert buf.n_accepted == 1


def test_buffer_flush_emits_everything_remaining():
    """flush() drains the heap completely."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=60)))
    buf.accept(event_at("E-1", 10))
    buf.accept(event_at("E-2", 20))
    buf.accept(event_at("E-3", 30))
    # No emits yet — watermark is way behind
    assert buf.n_buffered == 3
    final = buf.flush()
    assert buf.n_buffered == 0
    emitted = [r for r in final if r.disposition is EventDisposition.EMITTED]
    assert len(emitted) == 3


def test_buffer_zero_allowed_lateness_immediate_emit():
    """allowed_lateness=0 means watermark = max(event_time) — anything in
    the heap with event_time <= max is emitted immediately."""
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(0)))
    out = buf.accept(event_at("E-1", 100))
    emitted = [r for r in out if r.disposition is EventDisposition.EMITTED]
    assert len(emitted) == 1
    assert emitted[0].event.event_id == "E-1"


def test_buffer_punctuated_strategy_no_emit_until_punctuation():
    buf = LateArrivingBuffer(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=0),
        )
    )
    buf.accept(event_at("E-1", 10))
    buf.accept(event_at("E-2", 20))
    # No punctuation → still buffered
    assert buf.n_buffered == 2
    assert buf.n_emitted == 0
    # Now a punctuation arrives
    out = buf.accept(event_at("END-1", 20, is_punctuation=True))
    assert buf.n_emitted >= 2
    emitted_ids = {r.event.event_id for r in out if r.disposition is EventDisposition.EMITTED}
    assert "E-1" in emitted_ids
    assert "E-2" in emitted_ids


def test_buffer_n_accepted_tracks_unique_only():
    """n_accepted excludes duplicates."""
    buf = LateArrivingBuffer()
    buf.accept(event_at("E-1", 10))
    buf.accept(event_at("E-1", 10))
    buf.accept(event_at("E-2", 20))
    assert buf.n_accepted == 2
