"""JSONL event logging for circuit breaker snapshots."""

from __future__ import annotations

import json
import time

from circuitbreaker.breaker import CircuitBreaker, CircuitBreakerConfig, State


def snapshot_to_jsonl_line(cb: CircuitBreaker) -> str:
    snap = cb.snapshot()
    snap["timestamp_s"] = round(time.time(), 3)
    return json.dumps(snap, ensure_ascii=False)


def load_snapshots(text: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(raw)
    return out


def snapshot_state(raw: dict[str, object]) -> State:
    """Extract the State enum from a snapshot dict."""
    val = raw.get("state")
    if not isinstance(val, str):
        raise TypeError("state must be str")
    return State(val)


def config_from_dict(d: dict[str, object]) -> CircuitBreakerConfig:
    def _i(k: str, default: int) -> int:
        v = d.get(k, default)
        if not isinstance(v, int):
            raise TypeError(f"{k} must be int")
        return v

    def _f(k: str, default: float) -> float:
        v = d.get(k, default)
        if not isinstance(v, int | float):
            raise TypeError(f"{k} must be numeric")
        return float(v)

    def _s(k: str, default: str) -> str:
        v = d.get(k, default)
        if not isinstance(v, str):
            raise TypeError(f"{k} must be str")
        return v

    return CircuitBreakerConfig(
        failure_threshold=_i("failure_threshold", 5),
        reset_timeout_s=_f("reset_timeout_s", 30.0),
        success_threshold=_i("success_threshold", 2),
        probe_limit=_i("probe_limit", 3),
        name=_s("name", "default"),
    )


def build_from_snapshot(raw: dict[str, object]) -> CircuitBreaker:
    cfg = config_from_dict(raw)
    return CircuitBreaker(config=cfg)
