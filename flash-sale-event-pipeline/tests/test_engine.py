"""End-to-end StreamEngine tests."""

from __future__ import annotations

from flashpipe.engine import StreamEngine
from flashpipe.events import EventKind
from flashpipe.sinks import InMemoryHotnessSink, InMemoryWindowSink

from ._fixtures import make_event, t_at


def test_engine_drains_clean_stream():
    eng = StreamEngine(window_seconds=1, max_out_of_orderness_seconds=0)
    events = [make_event(event_id=f"E-{i}", created_at=t_at(i * 0.1)) for i in range(50)]
    sink = InMemoryWindowSink()
    eng.consume_many(events, window_sink=sink)
    assert sink.size > 0


def test_engine_late_event_is_dropped_and_counted():
    eng = StreamEngine(window_seconds=1, max_out_of_orderness_seconds=0)
    eng.consume(make_event(event_id="early", created_at=t_at(10)))
    eng.consume(make_event(event_id="late", created_at=t_at(5)))
    snap = eng.snapshot()
    assert snap.n_late_events == 1


def test_engine_fires_hot_product_on_burst():
    eng = StreamEngine(
        window_seconds=10,
        max_out_of_orderness_seconds=0,
        hot_min_views=10,
        hot_min_orders=5,
    )
    sink = InMemoryHotnessSink()
    for i in range(20):
        eng.consume(
            make_event(event_id=f"V-{i}", user_id=f"U-{i}", created_at=t_at(0.1 * i)),
            hotness_sink=sink,
        )
    # Close the window.
    eng.consume(make_event(event_id="trigger", created_at=t_at(100)), hotness_sink=sink)
    kinds = {h.kind.value for h in sink.received}
    assert "HOT_PRODUCT" in kinds


def test_engine_emits_window_aggregates_on_close():
    eng = StreamEngine(window_seconds=1, max_out_of_orderness_seconds=0)
    sink = InMemoryWindowSink()
    eng.consume(make_event(event_id="A", created_at=t_at(0.5)), window_sink=sink)
    eng.consume(make_event(event_id="B", created_at=t_at(10)), window_sink=sink)
    assert sink.size >= 1


def test_engine_flush_at_end_of_stream():
    eng = StreamEngine(window_seconds=1, max_out_of_orderness_seconds=0)
    sink = InMemoryWindowSink()
    eng.consume_many(
        [
            make_event(event_id="A", created_at=t_at(0.5)),
            make_event(event_id="B", created_at=t_at(1.5)),
        ],
        window_sink=sink,
    )
    # Both windows are flushed at end-of-stream.
    assert sink.size == 2


def test_engine_throughput_positive_after_run():
    eng = StreamEngine(window_seconds=1)
    eng.consume_many([make_event(event_id=f"E-{i}", created_at=t_at(i * 0.01)) for i in range(20)])
    snap = eng.snapshot()
    assert snap.throughput_events_per_sec > 0


def test_engine_order_event_aggregates_gmv():
    eng = StreamEngine(window_seconds=10)
    sink = InMemoryWindowSink()
    for i in range(5):
        eng.consume(
            make_event(
                event_id=f"O-{i}",
                kind=EventKind.ORDER,
                user_id=f"U-{i}",
                quantity=2,
                amount_vnd=100_000,
                created_at=t_at(0.1 * i),
            ),
            window_sink=sink,
        )
    # Force-close.
    eng.consume_many([make_event(event_id="X", created_at=t_at(100))], window_sink=sink)
    total_gmv = sum(a.gmv_vnd for a in sink.received)
    assert total_gmv >= 500_000


def test_engine_watermark_advances():
    eng = StreamEngine(window_seconds=1, max_out_of_orderness_seconds=2)
    eng.consume(make_event(event_id="E1", created_at=t_at(10)))
    assert eng.watermark == t_at(8)
    eng.consume(make_event(event_id="E2", created_at=t_at(20)))
    assert eng.watermark == t_at(18)
