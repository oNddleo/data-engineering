"""Property-based tests for circuit breaker."""

from __future__ import annotations

import contextlib

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from circuitbreaker.breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    State,
)


@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
    outcomes=st.lists(st.booleans(), min_size=1, max_size=50),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
def test_consecutive_failures_trip_open(failure_threshold: int, outcomes: list[bool]) -> None:
    """After failure_threshold consecutive failures, circuit must be OPEN."""
    cb = CircuitBreaker(
        config=CircuitBreakerConfig(failure_threshold=failure_threshold, reset_timeout_s=9999.0)
    )
    consec_failures = 0
    for success in outcomes:
        if cb.state == State.OPEN:
            break
        try:
            if success:
                cb.call(lambda: "ok")
                consec_failures = 0
            else:

                def _fail() -> str:
                    raise RuntimeError("x")

                cb.call(_fail)
                consec_failures += 1
        except (RuntimeError, CircuitOpenError):
            pass
        if consec_failures >= failure_threshold:
            assert cb.state == State.OPEN
            break


@given(
    n=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=30)
def test_metrics_total_failures_bounded(n: int) -> None:
    """total_failures <= total_calls + total_rejections always."""
    cb = CircuitBreaker(config=CircuitBreakerConfig(failure_threshold=100, reset_timeout_s=9999.0))

    def _fail() -> str:
        raise RuntimeError("x")

    for _ in range(n):
        with contextlib.suppress(RuntimeError, CircuitOpenError):
            cb.call(_fail)
    assert cb.metrics.total_failures <= cb.metrics.total_calls + cb.metrics.total_rejections


@given(
    failure_threshold=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=20)
def test_reset_always_returns_to_closed(failure_threshold: int) -> None:
    cb = CircuitBreaker(
        config=CircuitBreakerConfig(failure_threshold=failure_threshold, reset_timeout_s=9999.0)
    )

    def _fail() -> str:
        raise RuntimeError("x")

    for _ in range(failure_threshold):
        with contextlib.suppress(RuntimeError, CircuitOpenError):
            cb.call(_fail)
    cb.reset()
    assert cb.state == State.CLOSED


def test_open_circuit_never_executes_fn() -> None:
    """When OPEN, the wrapped function must never run."""
    cb = CircuitBreaker(config=CircuitBreakerConfig(failure_threshold=1, reset_timeout_s=9999.0))

    def _fail() -> str:
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        cb.call(_fail)

    executed: list[int] = []

    def _track() -> str:
        executed.append(1)
        return "ok"

    with pytest.raises(CircuitOpenError):
        cb.call(_track)
    assert executed == []  # fn was never called
