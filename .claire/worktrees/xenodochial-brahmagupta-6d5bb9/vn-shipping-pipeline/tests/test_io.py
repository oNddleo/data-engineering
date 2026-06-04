"""Tests for JSONL I/O utilities."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ivm.io.jsonl import dump_snapshot, load_snapshot, read_jsonl_updates


def test_dump_and_load_snapshot() -> None:
    records = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        path = f.name

    n = dump_snapshot(records, path)
    assert n == 2

    loaded = load_snapshot(path)
    assert loaded == records


def test_load_snapshot_empty_lines() -> None:
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write('{"x": 1}\n')
        f.write("\n")  # blank line
        f.write('{"x": 2}\n')
        path = f.name

    result = load_snapshot(path)
    assert len(result) == 2


def test_read_jsonl_updates() -> None:
    updates = [
        {"record": {"k": "a"}, "timestamp": 1000, "diff": 1},
        {"record": {"k": "b"}, "timestamp": 2000, "diff": -1},
    ]
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w",
                                     delete=False, encoding="utf-8") as f:
        for u in updates:
            f.write(json.dumps(u) + "\n")
        path = f.name

    result = read_jsonl_updates(path)
    assert len(result) == 2
    assert result[0].record == {"k": "a"}
    assert result[0].timestamp == 1000
    assert result[0].diff == 1
    assert result[1].diff == -1
