"""Tests for JSONL I/O."""

from __future__ import annotations

import io
import json

import pytest

from crdt.crdts import GCounter, GSet, PNCounter
from crdt.io_jsonl import (
    gcounter_from_dict,
    gcounter_to_dict,
    gset_from_dict,
    pncounter_from_dict,
    pncounter_to_dict,
    read_snapshot,
    write_snapshot,
)


class TestGCounterSerde:
    def test_roundtrip(self) -> None:
        c = GCounter({"n0": 3, "n1": 7})
        recovered = gcounter_from_dict(gcounter_to_dict(c))
        assert recovered == c

    def test_empty_counter(self) -> None:
        c = GCounter.new()
        assert gcounter_from_dict(gcounter_to_dict(c)) == c

    def test_bad_counts_type(self) -> None:
        with pytest.raises(TypeError):
            gcounter_from_dict({"type": "GCounter", "counts": "bad"})


class TestPNCounterSerde:
    def test_roundtrip(self) -> None:
        c = PNCounter.new().increment("n0", 5).decrement("n0", 2)
        recovered = pncounter_from_dict(pncounter_to_dict(c))
        assert recovered == c


class TestGSetSerde:
    def test_roundtrip(self) -> None:
        s = GSet.new("a", "b", "c")
        d = s.to_dict()
        recovered = gset_from_dict(d)
        assert recovered == s

    def test_bad_elements_type(self) -> None:
        with pytest.raises(TypeError):
            gset_from_dict({"elements": "bad"})


class TestSnapshotJSONL:
    def test_write_read_roundtrip(self) -> None:
        snaps = [
            {"crdt": "GCounter", "value": 5},
            {"crdt": "PNCounter", "value": 3},
        ]
        buf = io.StringIO()
        write_snapshot(snaps, buf)
        buf.seek(0)
        recovered = read_snapshot(buf)
        assert recovered == snaps

    def test_output_is_valid_jsonl(self) -> None:
        snaps = [{"x": i} for i in range(3)]
        buf = io.StringIO()
        write_snapshot(snaps, buf)
        for line in buf.getvalue().splitlines():
            json.loads(line)  # no exception

    def test_empty_file(self) -> None:
        buf = io.StringIO("")
        assert read_snapshot(buf) == []

    def test_blank_lines_skipped(self) -> None:
        buf = io.StringIO('\n{"a": 1}\n\n{"b": 2}\n')
        result = read_snapshot(buf)
        assert len(result) == 2
