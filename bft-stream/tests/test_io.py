"""Tests for JSONL I/O."""

from __future__ import annotations

import io
import json

import pytest

from bftstream.io_jsonl import (
    read_records,
    read_windows,
    record_from_dict,
    record_to_dict,
    window_from_dict,
    window_to_dict,
    write_records,
    write_windows,
)
from bftstream.schema import StreamRecord, WindowAggregate


def _rec(ts: float = 1.0, key: str = "k", value: float = 3.0, wid: int = 0) -> StreamRecord:
    return StreamRecord(timestamp=ts, key=key, value=value, window_id=wid)


def _win(wid: int = 0, count: int = 5, total: float = 15.0) -> WindowAggregate:
    w = WindowAggregate(window_id=wid)
    w.record_count = count
    w.value_sum = total
    w.committed = True
    return w


class TestRecordSerde:
    def test_roundtrip_dict(self) -> None:
        r = _rec()
        assert record_from_dict(record_to_dict(r)) == r

    def test_roundtrip_jsonl(self) -> None:
        records = [_rec(ts=float(i), wid=i) for i in range(5)]
        buf = io.StringIO()
        write_records(records, buf)
        buf.seek(0)
        assert read_records(buf) == records

    def test_bad_timestamp_raises(self) -> None:
        d = record_to_dict(_rec())
        d["timestamp"] = "bad"
        with pytest.raises(TypeError):
            record_from_dict(d)

    def test_bad_window_id_raises(self) -> None:
        d = record_to_dict(_rec())
        d["window_id"] = "zero"
        with pytest.raises(TypeError):
            record_from_dict(d)


class TestWindowSerde:
    def test_roundtrip_dict(self) -> None:
        w = _win()
        recovered = window_from_dict(window_to_dict(w))
        assert recovered.window_id == w.window_id
        assert recovered.record_count == w.record_count
        assert recovered.value_sum == pytest.approx(w.value_sum)

    def test_roundtrip_jsonl(self) -> None:
        windows = [_win(wid=i) for i in range(3)]
        buf = io.StringIO()
        write_windows(windows, buf)
        buf.seek(0)
        result = read_windows(buf)
        assert [r.window_id for r in result] == [0, 1, 2]

    def test_bad_value_sum_raises(self) -> None:
        d = window_to_dict(_win())
        d["value_sum"] = "bad"
        with pytest.raises(TypeError):
            window_from_dict(d)

    def test_read_empty(self) -> None:
        buf = io.StringIO("")
        assert read_records(buf) == []

    def test_jsonl_valid_json_lines(self) -> None:
        records = [_rec(ts=float(i)) for i in range(3)]
        buf = io.StringIO()
        write_records(records, buf)
        for line in buf.getvalue().splitlines():
            json.loads(line)  # should not raise
