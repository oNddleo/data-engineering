"""JSONL codec for keyed records and partition assignments."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

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


def dump_assignments(items: Iterable[tuple[str, int]]) -> str:
    return (
        "\n".join(json.dumps({"key": k, "partition": p}, ensure_ascii=False) for k, p in items)
        + "\n"
    )


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


def load_assignments(text: str) -> list[tuple[str, int]]:
    return [(_require_str(d, "key"), _require_int(d, "partition")) for d in _iter_lines(text)]


def dump_keys(items: Iterable[str]) -> str:
    return "\n".join(json.dumps({"key": k}, ensure_ascii=False) for k in items) + "\n"


def load_keys(text: str) -> list[str]:
    return [_require_str(d, "key") for d in _iter_lines(text)]


__all__ = ["dump_assignments", "dump_keys", "load_assignments", "load_keys"]
