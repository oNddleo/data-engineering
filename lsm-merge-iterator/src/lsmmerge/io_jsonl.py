"""JSONL codec for ``Record``."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from lsmmerge.schema import Record

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _opt_str(d: dict[str, object], key: str) -> str:
    v = d.get(key, "")
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _opt_bool(d: dict[str, object], key: str) -> bool:
    v = d.get(key, False)
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def record_to_dict(r: Record) -> dict[str, object]:
    return {
        "key": r.key,
        "seq": r.seq,
        "value": r.value,
        "tombstone": r.tombstone,
    }


def record_from_dict(d: dict[str, object]) -> Record:
    return Record(
        key=_require_str(d, "key"),
        seq=_require_int(d, "seq"),
        value=_opt_str(d, "value"),
        tombstone=_opt_bool(d, "tombstone"),
    )


def dump_records(records: Iterable[Record]) -> str:
    return "\n".join(json.dumps(record_to_dict(r), ensure_ascii=False) for r in records) + "\n"


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_records(text: str) -> list[Record]:
    return [record_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_records",
    "load_records",
    "record_from_dict",
    "record_to_dict",
]
