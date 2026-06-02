"""JSONL codec for keyed records."""

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


def dump_keys(items: Iterable[str]) -> str:
    return "\n".join(json.dumps({"key": k}, ensure_ascii=False) for k in items) + "\n"


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


def load_keys(text: str) -> list[str]:
    return [_require_str(d, "key") for d in _iter_lines(text)]


__all__ = ["dump_keys", "load_keys"]
