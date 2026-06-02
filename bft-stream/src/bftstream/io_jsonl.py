"""JSONL serialisation for stream records and window aggregates."""

from __future__ import annotations

import json
from typing import IO

from bftstream.schema import StreamRecord, WindowAggregate

# ── StreamRecord ──────────────────────────────────────────────────────────────


def record_to_dict(r: StreamRecord) -> dict[str, object]:
    return {
        "timestamp": r.timestamp,
        "key": r.key,
        "value": r.value,
        "window_id": r.window_id,
    }


def record_from_dict(obj: dict[str, object]) -> StreamRecord:
    ts = obj["timestamp"]
    val = obj["value"]
    wid = obj["window_id"]
    if not isinstance(ts, int | float):
        raise TypeError("timestamp must be numeric")
    if not isinstance(val, int | float):
        raise TypeError("value must be numeric")
    if not isinstance(wid, int):
        raise TypeError("window_id must be int")
    return StreamRecord(
        timestamp=float(ts),
        key=str(obj["key"]),
        value=float(val),
        window_id=wid,
    )


def _as_int(v: object) -> int:
    if not isinstance(v, int):
        raise TypeError(f"expected int, got {type(v).__name__}")
    return v


# ── WindowAggregate ───────────────────────────────────────────────────────────


def window_to_dict(w: WindowAggregate) -> dict[str, object]:
    return {
        "window_id": w.window_id,
        "record_count": w.record_count,
        "value_sum": w.value_sum,
        "checksum": w.checksum,
        "committed": w.committed,
    }


def window_from_dict(obj: dict[str, object]) -> WindowAggregate:
    wid = obj["window_id"]
    rc = obj["record_count"]
    vs = obj["value_sum"]
    if not isinstance(wid, int) or not isinstance(rc, int):
        raise TypeError("window_id and record_count must be int")
    if not isinstance(vs, int | float):
        raise TypeError("value_sum must be numeric")
    return WindowAggregate(
        window_id=wid,
        record_count=rc,
        value_sum=float(vs),
        checksum=_as_int(obj.get("checksum", 0)),
        committed=bool(obj.get("committed", False)),
    )


# ── JSONL I/O ────────────────────────────────────────────────────────────────


def write_records(records: list[StreamRecord], fh: IO[str]) -> None:
    for r in records:
        fh.write(json.dumps(record_to_dict(r)) + "\n")


def read_records(fh: IO[str]) -> list[StreamRecord]:
    out: list[StreamRecord] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(record_from_dict(json.loads(line)))
    return out


def write_windows(windows: list[WindowAggregate], fh: IO[str]) -> None:
    for w in windows:
        fh.write(json.dumps(window_to_dict(w)) + "\n")


def read_windows(fh: IO[str]) -> list[WindowAggregate]:
    out: list[WindowAggregate] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(window_from_dict(json.loads(line)))
    return out
