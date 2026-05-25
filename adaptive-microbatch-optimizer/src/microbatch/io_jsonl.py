"""JSONL serialisation for window-manager snapshots and simulation traces."""

from __future__ import annotations

import json
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from microbatch.window import WindowSnapshot


def snapshot_to_dict(s: WindowSnapshot) -> dict[str, object]:
    return {
        "window_size_s": s.window_size_s,
        "pid_error": s.pid_error,
        "backpressure_level": s.backpressure_level,
        "p95_latency": s.p95_latency,
        "throughput_eps": s.throughput_eps,
        "timestamp": s.timestamp,
    }


def snapshot_from_dict(obj: dict[str, object]) -> WindowSnapshot:
    def _float(key: str) -> float:
        v = obj[key]
        if not isinstance(v, int | float):
            raise TypeError(f"{key!r} must be numeric, got {type(v).__name__}")
        return float(v)

    def _opt_float(key: str) -> float | None:
        v = obj.get(key)
        if v is None:
            return None
        if not isinstance(v, int | float):
            raise TypeError(f"{key!r} must be numeric, got {type(v).__name__}")
        return float(v)

    return WindowSnapshot(
        window_size_s=_float("window_size_s"),
        pid_error=_float("pid_error"),
        backpressure_level=_float("backpressure_level"),
        p95_latency=_opt_float("p95_latency"),
        throughput_eps=_opt_float("throughput_eps"),
        timestamp=_float("timestamp"),
    )


def write_snapshots(snapshots: list[WindowSnapshot], fh: IO[str]) -> None:
    for s in snapshots:
        fh.write(json.dumps(snapshot_to_dict(s)) + "\n")


def read_snapshots(fh: IO[str]) -> list[WindowSnapshot]:
    out: list[WindowSnapshot] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(snapshot_from_dict(json.loads(line)))
    return out


def write_snapshots_path(snapshots: list[WindowSnapshot], path: Path) -> None:
    with path.open("w") as fh:
        write_snapshots(snapshots, fh)


def read_snapshots_path(path: Path) -> list[WindowSnapshot]:
    with path.open() as fh:
        return read_snapshots(fh)
