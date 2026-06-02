"""JSONL codec for rate limiter snapshots."""

from __future__ import annotations

import json

from ratelimiter.sliding_window import SlidingWindowCounter
from ratelimiter.token_bucket import TokenBucket


def dump(limiters: list[TokenBucket | SlidingWindowCounter]) -> str:
    lines = [json.dumps(limiter.snapshot(), ensure_ascii=False) for limiter in limiters]
    return "\n".join(lines) + ("\n" if lines else "")


def _req_float(d: dict[str, object], k: str) -> float:
    v = d.get(k)
    if not isinstance(v, int | float):
        raise TypeError(f"{k} must be numeric")
    return float(v)


def _req_int(d: dict[str, object], k: str) -> int:
    v = d.get(k)
    if not isinstance(v, int):
        raise TypeError(f"{k} must be int")
    return v


def _req_str(d: dict[str, object], k: str) -> str:
    v = d.get(k)
    if not isinstance(v, str):
        raise TypeError(f"{k} must be str")
    return v


def _parse_dict(line: str) -> dict[str, object]:
    raw = json.loads(line)
    if not isinstance(raw, dict):
        raise TypeError(f"Expected dict, got {type(raw)}")
    return raw


def load_token_buckets(text: str) -> list[TokenBucket]:
    out: list[TokenBucket] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        d = _parse_dict(line)
        tb = TokenBucket(
            capacity=_req_float(d, "capacity"),
            refill_rate=_req_float(d, "refill_rate"),
            name=_req_str(d, "name"),
        )
        tb._tokens = _req_float(d, "tokens")
        out.append(tb)
    return out


def load_sliding_windows(text: str) -> list[SlidingWindowCounter]:
    out: list[SlidingWindowCounter] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        d = _parse_dict(line)
        out.append(
            SlidingWindowCounter(
                limit=_req_int(d, "limit"),
                window_s=_req_float(d, "window_s"),
                name=_req_str(d, "name"),
            )
        )
    return out
