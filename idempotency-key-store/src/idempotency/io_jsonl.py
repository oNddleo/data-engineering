"""JSONL codec for IdempotencyEntry."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from idempotency.schema import EntryStatus, IdempotencyEntry

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


def to_dict(e: IdempotencyEntry) -> dict[str, object]:
    return {
        "key": e.key,
        "request_fingerprint": e.request_fingerprint,
        "status": e.status.value,
        "response_body": e.response_body,
        "created_at_ms": e.created_at_ms,
        "expires_at_ms": e.expires_at_ms,
    }


def from_dict(d: dict[str, object]) -> IdempotencyEntry:
    return IdempotencyEntry(
        key=_require_str(d, "key"),
        request_fingerprint=_require_str(d, "request_fingerprint"),
        status=EntryStatus(_require_str(d, "status")),
        response_body=_require_str(d, "response_body"),
        created_at_ms=_require_int(d, "created_at_ms"),
        expires_at_ms=_require_int(d, "expires_at_ms"),
    )


def dump(items: Iterable[IdempotencyEntry]) -> str:
    return "\n".join(json.dumps(to_dict(e), ensure_ascii=False) for e in items) + "\n"


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


def load(text: str) -> list[IdempotencyEntry]:
    return [from_dict(d) for d in _iter_lines(text)]


__all__ = ["dump", "from_dict", "load", "to_dict"]
