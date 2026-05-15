"""Simulator + integration tests."""

from __future__ import annotations

import pytest

from flashpipe.detectors import HotnessKind
from flashpipe.engine import StreamEngine
from flashpipe.simulator import generate
from flashpipe.sinks import InMemoryHotnessSink


def test_generate_reproducible_with_seed():
    a = generate(seed=42, n_events=20)
    b = generate(seed=42, n_events=20)
    assert [e.event_id for e in a] == [e.event_id for e in b]


def test_generate_count_matches_arg():
    events = generate(seed=0, n_events=500)
    # Baseline only — no stampede injection adds more.
    assert len(events) == 500


def test_generate_stampede_injection_adds_burst():
    base = generate(seed=0, n_events=100, n_items=10)
    with_stampede = generate(seed=0, n_events=100, n_items=10, inject_stampede_item=100_000)
    assert len(with_stampede) == len(base) + 200


def test_generate_stampede_fires_detector():
    events = generate(
        seed=1,
        n_events=100,
        n_items=10,
        inject_stampede_item=100_005,
    )
    # Sort by event time to feed in order — production Kafka order may differ.
    events.sort(key=lambda e: e.created_at)
    eng = StreamEngine(
        window_seconds=1,
        max_out_of_orderness_seconds=0,
        stampede_multiplier=5.0,
        stampede_min_baseline=2,
    )
    sink = InMemoryHotnessSink()
    eng.consume_many(events, hotness_sink=sink)
    kinds = {h.kind for h in sink.received}
    assert HotnessKind.STAMPEDE in kinds


def test_generate_disorder_increases_late_events():
    """When out_of_order_fraction is high, the engine drops more events as late."""
    events_clean = generate(seed=1, n_events=100)
    events_messy = generate(seed=1, n_events=100, out_of_order_fraction=0.3)
    eng_clean = StreamEngine(max_out_of_orderness_seconds=0.5)
    eng_messy = StreamEngine(max_out_of_orderness_seconds=0.5)
    eng_clean.consume_many(events_clean)
    eng_messy.consume_many(events_messy)
    # Some late drops expected on the messy stream.
    assert eng_messy.snapshot().n_late_events >= eng_clean.snapshot().n_late_events


def test_generate_rejects_bad_disorder():
    with pytest.raises(ValueError):
        generate(out_of_order_fraction=1.5)
    with pytest.raises(ValueError):
        generate(out_of_order_fraction=-0.1)
