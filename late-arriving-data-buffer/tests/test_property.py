"""Hypothesis properties — invariants of the buffer + watermarks."""

from __future__ import annotations

from datetime import timedelta
from itertools import pairwise

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from latebuf.buffer import LateArrivingBuffer
from latebuf.metrics import compute_stats
from latebuf.schema import (
    BufferConfig,
    EventDisposition,
    WatermarkStrategy,
)
from latebuf.simulator import generate
from latebuf.watermark import new_watermark

from ._fixtures import event_at


@given(
    n=st.integers(min_value=10, max_value=200),
    seed=st.integers(min_value=0, max_value=1_000),
    allowed=st.integers(min_value=1, max_value=60),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_buffer_accounting_balanced(
    n: int,
    seed: int,
    allowed: int,
) -> None:
    """``n_accepted == n_emitted + n_dead_lettered + n_still_buffered``."""
    events = generate(n_events=n, seed=seed, max_lateness_seconds=30)
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=allowed)))
    for e in events:
        buf.accept(e)
    buf.flush()
    assert buf.n_accepted == buf.n_emitted + buf.n_dead_lettered + buf.n_buffered


@given(
    n=st.integers(min_value=10, max_value=100),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_high_lateness_eliminates_drops(n: int, seed: int) -> None:
    """A very large ``allowed_lateness`` should never dead-letter events."""
    events = generate(n_events=n, seed=seed, max_lateness_seconds=30)
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(hours=1)))
    for e in events:
        buf.accept(e)
    buf.flush()
    assert buf.n_dead_lettered == 0


@given(
    n=st.integers(min_value=10, max_value=100),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_emit_is_event_time_sorted(n: int, seed: int) -> None:
    """The emit stream is sorted by event-time (among EMITTED records)."""
    events = generate(n_events=n, seed=seed, max_lateness_seconds=30)
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=60)))
    emitted = []
    for e in events:
        emitted.extend(buf.accept(e))
    emitted.extend(buf.flush())
    on_time = [r for r in emitted if r.disposition is EventDisposition.EMITTED]
    times = [r.event.event_time for r in on_time]
    for prev, curr in pairwise(times):
        assert curr >= prev


@given(
    n=st.integers(min_value=5, max_value=100),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_watermark_monotonic(n: int, seed: int) -> None:
    """The watermark only ever advances forward."""
    events = generate(n_events=n, seed=seed, max_lateness_seconds=30)
    wm = new_watermark(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    last = None
    for e in events:
        advance = wm.update(e)
        if advance is not None:
            if last is not None:
                assert advance >= last
            last = advance


@given(
    n=st.integers(min_value=10, max_value=100),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_stats_consistent_with_buffer(n: int, seed: int) -> None:
    """compute_stats() values match buffer instance counters."""
    events = generate(n_events=n, seed=seed, max_lateness_seconds=30)
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=10)))
    for e in events:
        buf.accept(e)
    buf.flush()
    s = compute_stats(buf)
    assert s.n_accepted == buf.n_accepted
    assert s.n_emitted == buf.n_emitted
    assert s.n_dead_lettered == buf.n_dead_lettered


@given(
    event_offsets=st.lists(
        st.integers(min_value=0, max_value=300),
        min_size=2,
        max_size=30,
        unique=True,
    ),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=15)
def test_property_dedup_idempotent_per_id(
    event_offsets: list[int],
    seed: int,
) -> None:
    """Submitting the same event_id twice → n_accepted increments once."""
    import random

    rng = random.Random(seed)
    events = [event_at(f"E-{i}", off) for i, off in enumerate(event_offsets)]
    # Duplicate one event
    dup = rng.choice(events)
    buf = LateArrivingBuffer(BufferConfig(allowed_lateness=timedelta(seconds=600)))
    for e in events:
        buf.accept(e)
    initial = buf.n_accepted
    buf.accept(dup)
    assert buf.n_accepted == initial


@given(
    n=st.integers(min_value=5, max_value=50),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_punctuated_strategy_emits_only_on_punct(
    n: int,
    seed: int,
) -> None:
    """Without any punctuation, PUNCTUATED strategy emits nothing via accept()
    (everything sits in the heap until flush)."""
    events = generate(
        n_events=n, seed=seed, max_lateness_seconds=10, punctuation_every=10_000
    )  # effectively none
    buf = LateArrivingBuffer(
        BufferConfig(
            strategy=WatermarkStrategy.PUNCTUATED,
            allowed_lateness=timedelta(seconds=0),
        )
    )
    for e in events:
        out = buf.accept(e)
        emitted = [r for r in out if r.disposition is EventDisposition.EMITTED]
        # No punctuation → no in-flight emits.
        assert not emitted


@given(
    config=st.builds(
        BufferConfig,
        allowed_lateness=st.timedeltas(
            min_value=timedelta(0),
            max_value=timedelta(seconds=120),
        ),
    ),
)
@settings(max_examples=20)
def test_property_zero_events_zero_stats(config: BufferConfig) -> None:
    """An untouched buffer produces all-zero stats."""
    buf = LateArrivingBuffer(config)
    s = compute_stats(buf)
    assert s.n_accepted == 0
    assert s.n_emitted == 0
    assert s.n_dead_lettered == 0
