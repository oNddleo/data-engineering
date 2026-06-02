"""Unit tests for circuit breaker state machine."""

from __future__ import annotations

import time

import pytest

from circuitbreaker.breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    State,
)


def _cb(
    failure_threshold: int = 3,
    reset_timeout_s: float = 0.05,
    success_threshold: int = 2,
    probe_limit: int = 5,
) -> CircuitBreaker:
    return CircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            reset_timeout_s=reset_timeout_s,
            success_threshold=success_threshold,
            probe_limit=probe_limit,
        )
    )


def _succeed() -> str:
    return "ok"


def _fail() -> str:
    raise RuntimeError("boom")


class TestClosedState:
    def test_starts_closed(self) -> None:
        cb = _cb()
        assert cb.state == State.CLOSED

    def test_success_stays_closed(self) -> None:
        cb = _cb()
        for _ in range(10):
            cb.call(_succeed)
        assert cb.state == State.CLOSED

    def test_failure_below_threshold_stays_closed(self) -> None:
        cb = _cb(failure_threshold=3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        assert cb.state == State.CLOSED

    def test_consecutive_failures_trip_open(self) -> None:
        cb = _cb(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        assert cb.state == State.OPEN

    def test_success_resets_failure_counter(self) -> None:
        cb = _cb(failure_threshold=3)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        cb.call(_succeed)  # reset counter
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == State.CLOSED  # still 2 consec failures


class TestOpenState:
    def test_open_rejects_calls(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=60.0)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == State.OPEN
        with pytest.raises(CircuitOpenError):
            cb.call(_succeed)

    def test_open_rejection_increments_counter(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=60.0)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        for _ in range(3):
            with pytest.raises(CircuitOpenError):
                cb.call(_succeed)
        assert cb.metrics.total_rejections == 3

    def test_circuit_open_error_has_retry_after(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=30.0)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        try:
            cb.call(_succeed)
        except CircuitOpenError as e:
            assert e.retry_after_s > 0
            assert e.name == "default"
        else:
            pytest.fail("Expected CircuitOpenError")

    def test_transitions_to_half_open_after_timeout(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=0.05)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == State.OPEN
        time.sleep(0.06)
        assert cb.state == State.HALF_OPEN


class TestHalfOpenState:
    def test_success_in_half_open_closes(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=0.05, success_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        time.sleep(0.06)
        assert cb.state == State.HALF_OPEN
        cb.call(_succeed)
        cb.call(_succeed)
        assert cb.state == State.CLOSED

    def test_failure_in_half_open_trips_open(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=0.05)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        time.sleep(0.06)
        assert cb.state == State.HALF_OPEN
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == State.OPEN

    def test_probe_limit_forces_open(self) -> None:
        cb = _cb(failure_threshold=1, reset_timeout_s=0.05, probe_limit=2, success_threshold=5)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        time.sleep(0.06)
        # Use up probe limit with successes (not enough to close)
        cb.call(_succeed)
        cb.call(_succeed)
        # 3rd probe should be rejected (probe_limit=2)
        with pytest.raises(CircuitOpenError):
            cb.call(_succeed)


class TestReset:
    def test_manual_reset_closes_circuit(self) -> None:
        cb = _cb(failure_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == State.OPEN
        cb.reset()
        assert cb.state == State.CLOSED

    def test_force_open(self) -> None:
        cb = _cb()
        assert cb.state == State.CLOSED
        cb.force_open()
        assert cb.state == State.OPEN

    def test_reset_clears_metrics(self) -> None:
        cb = _cb(failure_threshold=3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        cb.reset()
        assert cb.metrics.consecutive_failures == 0
        assert cb.metrics.total_failures == 0


class TestSnapshot:
    def test_snapshot_keys(self) -> None:
        cb = _cb()
        snap = cb.snapshot()
        assert "name" in snap
        assert "state" in snap
        assert "total_calls" in snap
        assert "total_failures" in snap
        assert "total_rejections" in snap

    def test_snapshot_state_value(self) -> None:
        cb = _cb()
        snap = cb.snapshot()
        assert snap["state"] == "CLOSED"


class TestConfig:
    def test_invalid_failure_threshold(self) -> None:
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_invalid_reset_timeout(self) -> None:
        with pytest.raises(ValueError):
            CircuitBreakerConfig(reset_timeout_s=0.0)

    def test_invalid_success_threshold(self) -> None:
        with pytest.raises(ValueError):
            CircuitBreakerConfig(success_threshold=0)
