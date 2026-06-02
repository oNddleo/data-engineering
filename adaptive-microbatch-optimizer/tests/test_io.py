"""Tests for JSONL I/O."""

from __future__ import annotations

import io
import json

import pytest

from microbatch.io_jsonl import (
    read_snapshots,
    snapshot_from_dict,
    snapshot_to_dict,
    write_snapshots,
)
from microbatch.window import WindowSnapshot


def _snap(w: float = 0.5, err: float = 0.1, bp: float = 0.2) -> WindowSnapshot:
    return WindowSnapshot(
        window_size_s=w,
        pid_error=err,
        backpressure_level=bp,
        p95_latency=0.18,
        throughput_eps=500.0,
        timestamp=1_700_000_000.0,
    )


class TestSnapshotSerde:
    def test_roundtrip_dict(self) -> None:
        s = _snap()
        assert snapshot_from_dict(snapshot_to_dict(s)) == s

    def test_roundtrip_jsonl(self) -> None:
        snaps = [_snap(w=0.3), _snap(w=0.7)]
        buf = io.StringIO()
        write_snapshots(snaps, buf)
        buf.seek(0)
        recovered = read_snapshots(buf)
        assert recovered == snaps

    def test_null_latency_roundtrip(self) -> None:
        s = WindowSnapshot(
            window_size_s=1.0,
            pid_error=0.0,
            backpressure_level=0.0,
            p95_latency=None,
            throughput_eps=None,
            timestamp=0.0,
        )
        d = snapshot_to_dict(s)
        assert d["p95_latency"] is None
        assert snapshot_from_dict(d) == s

    def test_bad_type_raises(self) -> None:
        d = snapshot_to_dict(_snap())
        d["window_size_s"] = "bad"
        with pytest.raises(TypeError):
            snapshot_from_dict(d)

    def test_jsonl_output_lines(self) -> None:
        snaps = [_snap()] * 3
        buf = io.StringIO()
        write_snapshots(snaps, buf)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        assert len(lines) == 3
        json.loads(lines[0])  # valid JSON

    def test_read_empty(self) -> None:
        buf = io.StringIO("")
        assert read_snapshots(buf) == []

    def test_read_skips_blank_lines(self) -> None:
        s = _snap()
        buf = io.StringIO("\n" + json.dumps(snapshot_to_dict(s)) + "\n\n")
        result = read_snapshots(buf)
        assert len(result) == 1
        assert result[0] == s
