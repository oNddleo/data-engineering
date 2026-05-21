"""JSONL codec for Record."""

from __future__ import annotations

import json

from retention.schema import Record


def record_to_dict(r: Record) -> dict[str, object]:
    return {
        "key": r.key,
        "created_at_ms": r.created_at_ms,
        "size_bytes": r.size_bytes,
        "tags": sorted(r.tags),
    }


def record_from_dict(d: object) -> Record:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")
    key = d.get("key")
    if not isinstance(key, str):
        raise TypeError("key must be str")
    created = d.get("created_at_ms")
    if not isinstance(created, int):
        raise TypeError("created_at_ms must be int")
    size = d.get("size_bytes")
    if not isinstance(size, int):
        raise TypeError("size_bytes must be int")
    tags_raw = d.get("tags", [])
    if not isinstance(tags_raw, list):
        raise TypeError("tags must be a list")
    tags = frozenset(str(t) for t in tags_raw)
    return Record(key=key, created_at_ms=created, size_bytes=size, tags=tags)


def dump(records: list[Record]) -> str:
    lines = [json.dumps(record_to_dict(r), ensure_ascii=False) for r in records]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[Record]:
    out: list[Record] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(record_from_dict(raw))
    return out
