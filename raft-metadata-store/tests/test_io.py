"""Tests for JSONL I/O of log entries and snapshots."""

from __future__ import annotations

import io
import json

import pytest

from raftmeta.io_jsonl import (
    entry_from_dict,
    entry_to_dict,
    read_log,
    write_log,
    write_snapshot,
)
from raftmeta.schema import LogEntry
from raftmeta.store import MetadataStore


def _entry(term: int = 1, index: int = 0, cmd: str = "SET x 1") -> LogEntry:
    return LogEntry(term=term, index=index, command=cmd, client_id="c1")


class TestLogEntryIO:
    def test_roundtrip_dict(self) -> None:
        e = _entry()
        d = entry_to_dict(e)
        e2 = entry_from_dict(d)
        assert e == e2

    def test_roundtrip_jsonl(self) -> None:
        entries = [_entry(term=1, index=i, cmd=f"SET k{i} v{i}") for i in range(5)]
        buf = io.StringIO()
        write_log(entries, buf)
        buf.seek(0)
        loaded = read_log(buf)
        assert len(loaded) == 5
        assert loaded[2].command == "SET k2 v2"

    def test_empty_log(self) -> None:
        buf = io.StringIO()
        write_log([], buf)
        buf.seek(0)
        assert read_log(buf) == []

    def test_missing_client_id_defaults(self) -> None:
        d: dict[str, object] = {"term": 2, "index": 3, "command": "DEL y"}
        e = entry_from_dict(d)
        assert e.client_id == ""

    def test_bad_term_type_raises(self) -> None:
        d: dict[str, object] = {"term": "bad", "index": 0, "command": "SET x 1"}
        with pytest.raises((ValueError, TypeError)):
            entry_from_dict(d)


class TestSnapshotIO:
    def test_snapshot_contains_all_nodes(self) -> None:
        store = MetadataStore(node_ids=["a", "b", "c"], seed=2)
        store.set("x", "1")
        buf = io.StringIO()
        write_snapshot(store.cluster.nodes, buf)  # type: ignore[arg-type]
        buf.seek(0)
        rows = [json.loads(ln) for ln in buf if ln.strip()]
        node_ids = {r["node_id"] for r in rows}
        assert node_ids == {"a", "b", "c"}

    def test_snapshot_has_kv(self) -> None:
        store = MetadataStore(node_ids=["a", "b", "c"], seed=3)
        store.set("meta_key", "meta_val")
        ldr = store.leader
        buf = io.StringIO()
        write_snapshot(store.cluster.nodes, buf)  # type: ignore[arg-type]
        buf.seek(0)
        rows = {r["node_id"]: r for r in (json.loads(ln) for ln in buf if ln.strip())}
        assert rows[ldr]["kv"].get("meta_key") == "meta_val"
