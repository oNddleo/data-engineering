"""JSONL I/O tests for circuit breaker."""

from __future__ import annotations

from circuitbreaker.breaker import CircuitBreaker, CircuitBreakerConfig, State
from circuitbreaker.io_jsonl import (
    build_from_snapshot,
    config_from_dict,
    load_snapshots,
    snapshot_state,
    snapshot_to_jsonl_line,
)


def _cb() -> CircuitBreaker:
    return CircuitBreaker(config=CircuitBreakerConfig(name="test-cb"))


def test_snapshot_to_jsonl_line_is_valid_json() -> None:
    import json

    cb = _cb()
    line = snapshot_to_jsonl_line(cb)
    obj = json.loads(line)
    assert obj["state"] == "CLOSED"
    assert "timestamp_s" in obj


def test_load_snapshots_empty() -> None:
    assert load_snapshots("") == []


def test_load_snapshots_single() -> None:
    cb = _cb()
    line = snapshot_to_jsonl_line(cb)
    loaded = load_snapshots(line)
    assert len(loaded) == 1
    assert loaded[0]["name"] == "test-cb"


def test_snapshot_state_extraction() -> None:
    snap: dict[str, object] = {"state": "OPEN"}
    assert snapshot_state(snap) == State.OPEN


def test_config_from_dict() -> None:
    d: dict[str, object] = {
        "failure_threshold": 5,
        "reset_timeout_s": 60.0,
        "success_threshold": 3,
        "probe_limit": 4,
        "name": "my-breaker",
    }
    cfg = config_from_dict(d)
    assert cfg.failure_threshold == 5
    assert cfg.reset_timeout_s == 60.0
    assert cfg.name == "my-breaker"


def test_build_from_snapshot_returns_circuit_breaker() -> None:
    d: dict[str, object] = {"name": "test", "failure_threshold": 3}
    cb = build_from_snapshot(d)
    assert isinstance(cb, CircuitBreaker)
    assert cb.state == State.CLOSED
