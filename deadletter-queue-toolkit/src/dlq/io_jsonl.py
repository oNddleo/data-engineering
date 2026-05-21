"""JSONL codec for DeadLetter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dlq.schema import DeadLetter, FailureKind

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


def _opt_headers(d: dict[str, object]) -> dict[str, str]:
    raw = d.get("headers", {})
    if not isinstance(raw, dict):
        raise TypeError("headers must be an object")
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise TypeError("headers must map str → str")
        out[k] = v
    return out


def to_dict(dl: DeadLetter) -> dict[str, object]:
    return {
        "message_id": dl.message_id,
        "payload": dl.payload,
        "original_topic": dl.original_topic,
        "failure_kind": dl.failure_kind.value,
        "error_message": dl.error_message,
        "retry_count": dl.retry_count,
        "first_failed_at_ms": dl.first_failed_at_ms,
        "last_failed_at_ms": dl.last_failed_at_ms,
        "headers": dict(dl.headers),
    }


def from_dict(d: dict[str, object]) -> DeadLetter:
    return DeadLetter(
        message_id=_require_str(d, "message_id"),
        payload=_require_str(d, "payload"),
        original_topic=_require_str(d, "original_topic"),
        failure_kind=FailureKind(_require_str(d, "failure_kind")),
        error_message=_require_str(d, "error_message"),
        retry_count=_require_int(d, "retry_count"),
        first_failed_at_ms=_require_int(d, "first_failed_at_ms"),
        last_failed_at_ms=_require_int(d, "last_failed_at_ms"),
        headers=_opt_headers(d),
    )


def dump(items: Iterable[DeadLetter]) -> str:
    return "\n".join(json.dumps(to_dict(dl), ensure_ascii=False) for dl in items) + "\n"


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


def load(text: str) -> list[DeadLetter]:
    return [from_dict(d) for d in _iter_lines(text)]


__all__ = ["dump", "from_dict", "load", "to_dict"]
