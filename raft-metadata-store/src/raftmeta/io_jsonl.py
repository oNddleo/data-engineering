"""JSONL serialisation for Raft log entries and cluster snapshots."""

from __future__ import annotations

import json
from typing import IO

from raftmeta.schema import LogEntry

# ── LogEntry ──────────────────────────────────────────────────────────────────


def entry_to_dict(e: LogEntry) -> dict[str, object]:
    return {
        "term": e.term,
        "index": e.index,
        "command": e.command,
        "client_id": e.client_id,
    }


def entry_from_dict(obj: dict[str, object]) -> LogEntry:
    t = obj["term"]
    i = obj["index"]
    if not isinstance(t, int) or not isinstance(i, int):
        raise TypeError("term and index must be int")
    return LogEntry(
        term=t,
        index=i,
        command=str(obj["command"]),
        client_id=str(obj.get("client_id", "")),
    )


# ── Cluster snapshot ──────────────────────────────────────────────────────────


def snapshot_cluster(nodes: dict[str, object]) -> list[dict[str, object]]:
    """Serialise cluster node states to a list of dicts."""
    from raftmeta.node import RaftNode  # noqa: TCH001

    result: list[dict[str, object]] = []
    for nid, node in nodes.items():
        if not isinstance(node, RaftNode):
            continue
        result.append(
            {
                "node_id": nid,
                "state": node.state.value,
                "term": node.current_term,
                "commit_index": node.commit_index,
                "last_applied": node.last_applied,
                "log_length": len(node.log),
                "kv": dict(node.kv),
            }
        )
    return result


def write_snapshot(nodes: dict[str, object], fh: IO[str]) -> None:
    """Write per-node state as JSONL."""
    for row in snapshot_cluster(nodes):
        fh.write(json.dumps(row) + "\n")


def write_log(log: list[LogEntry], fh: IO[str]) -> None:
    """Write a Raft log as JSONL."""
    for entry in log:
        fh.write(json.dumps(entry_to_dict(entry)) + "\n")


def read_log(fh: IO[str]) -> list[LogEntry]:
    """Read a JSONL log file."""
    entries: list[LogEntry] = []
    for line in fh:
        line = line.strip()
        if line:
            entries.append(entry_from_dict(json.loads(line)))
    return entries
