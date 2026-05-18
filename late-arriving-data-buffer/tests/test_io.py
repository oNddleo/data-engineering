"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from latebuf.io_jsonl import (
    dump_emitted,
    dump_events,
    emitted_from_dict,
    emitted_to_dict,
    event_from_dict,
    event_to_dict,
    load_emitted,
    load_events,
    stats_from_dict,
    stats_to_dict,
)
from latebuf.schema import (
    VN_TZ,
    BufferStats,
    EmittedRecord,
    EventDisposition,
)

from ._fixtures import DEFAULT_TS, event_at, make_event


def test_event_round_trip():
    e = make_event(payload="hello", is_punctuation=True)
    assert event_from_dict(event_to_dict(e)) == e


def test_event_dump_load_many():
    events = [event_at(f"E-{i}", i) for i in range(10)]
    assert load_events(dump_events(events)) == events


def test_event_dump_newline_terminated():
    e = make_event()
    text = dump_events([e])
    assert text.endswith("\n")
    assert text.count("\n") == 1


def test_event_load_skips_blank_lines():
    e = make_event()
    raw = dump_events([e]) + "\n  \n"
    assert load_events(raw) == [e]


def test_event_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_events("[1, 2]\n")


def test_event_load_rejects_str_punctuation():
    """A str sneaking in as bool must be rejected."""
    bad = event_to_dict(make_event())
    bad["is_punctuation"] = "true"
    with pytest.raises(TypeError, match="is_punctuation must be bool"):
        event_from_dict(bad)


def test_emitted_record_round_trip():
    r = EmittedRecord(
        event=make_event(event_id="E-99"),
        disposition=EventDisposition.DEAD_LETTERED,
        lateness_seconds=42,
    )
    assert emitted_from_dict(emitted_to_dict(r)) == r


def test_emitted_dump_load():
    records = [
        EmittedRecord(
            event=event_at(f"E-{i}", i),
            disposition=EventDisposition.EMITTED,
            lateness_seconds=0,
        )
        for i in range(5)
    ]
    assert load_emitted(dump_emitted(records)) == records


def test_emitted_load_rejects_non_dict_event():
    bad = emitted_to_dict(
        EmittedRecord(
            event=make_event(),
            disposition=EventDisposition.EMITTED,
            lateness_seconds=0,
        )
    )
    bad["event"] = 42
    with pytest.raises(TypeError, match="event must be dict"):
        emitted_from_dict(bad)


def test_stats_round_trip():
    s = BufferStats(
        n_accepted=100,
        n_emitted=90,
        n_dead_lettered=10,
        n_still_buffered=0,
        max_lateness_seconds=15,
        median_lateness_seconds=7,
        p99_lateness_seconds=14,
        final_watermark=DEFAULT_TS + timedelta(seconds=200),
    )
    assert stats_from_dict(stats_to_dict(s)) == s


def test_stats_round_trip_no_watermark():
    s = BufferStats(
        n_accepted=0,
        n_emitted=0,
        n_dead_lettered=0,
        n_still_buffered=0,
        max_lateness_seconds=0,
        median_lateness_seconds=0,
        p99_lateness_seconds=0,
    )
    out = stats_from_dict(stats_to_dict(s))
    assert out.final_watermark is None


def test_event_dump_load_uses_vn_tz():
    """Times round-trip with their original timezone offset preserved."""
    t = datetime(2026, 5, 18, 12, 0, 0, tzinfo=VN_TZ)
    e = make_event(event_time=t, ingest_time=t)
    out = event_from_dict(event_to_dict(e))
    assert out.event_time.utcoffset() == VN_TZ.utcoffset(None)
