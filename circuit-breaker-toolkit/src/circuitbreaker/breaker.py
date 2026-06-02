"""Circuit breaker state machine.

States:
  CLOSED    → Normal operation. Failures increment counter.
              If failures >= failure_threshold within window → OPEN.
  OPEN      → All calls rejected immediately (fail-fast).
              After reset_timeout_s → HALF_OPEN.
  HALF_OPEN → Probe: allow up to probe_limit calls through.
              If success_threshold successes → CLOSED.
              Any failure → OPEN.

Failure window: sliding count (not time-based) — simpler and deterministic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class State(str, Enum):
    """Circuit breaker state."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised when a call is attempted on an OPEN circuit."""

    def __init__(self, name: str, retry_after_s: float) -> None:
        self.name = name
        self.retry_after_s = retry_after_s
        super().__init__(f"Circuit '{name}' is OPEN. Retry after {retry_after_s:.1f}s.")


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker.

    Args:
        failure_threshold:   Number of consecutive failures to trip OPEN.
        reset_timeout_s:     Seconds to wait in OPEN before probing (HALF_OPEN).
        success_threshold:   Consecutive successes in HALF_OPEN to close circuit.
        probe_limit:         Max calls allowed through in HALF_OPEN before forcing OPEN.
        name:                Human-readable identifier.
    """

    failure_threshold: int = 5
    reset_timeout_s: float = 30.0
    success_threshold: int = 2
    probe_limit: int = 3
    name: str = "default"

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.reset_timeout_s <= 0:
            raise ValueError("reset_timeout_s must be > 0")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.probe_limit < 1:
            raise ValueError("probe_limit must be >= 1")


@dataclass
class _Metrics:
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    probe_count: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_rejections: int = 0


@dataclass
class CircuitBreaker:
    """Thread-safe circuit breaker implementation.

    Usage::

        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        def call_service() -> str:
            # ... call downstream
            return "ok"

        try:
            result = cb.call(call_service)
        except CircuitOpenError:
            # fast-fail path
            result = cached_value
    """

    config: CircuitBreakerConfig

    _state: State = field(default=State.CLOSED, init=False)
    _metrics: _Metrics = field(default_factory=_Metrics, init=False)
    _opened_at: float = field(default=0.0, init=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> State:
        """Current circuit state (may transition OPEN→HALF_OPEN on read)."""
        self._maybe_transition_to_half_open()
        return self._state

    @property
    def metrics(self) -> _Metrics:
        return self._metrics

    def call(self, fn: Callable[[], T], *args: object, **kwargs: object) -> T:
        """Execute *fn* through the circuit breaker.

        Raises:
            CircuitOpenError: If the circuit is OPEN.
        """
        self._maybe_transition_to_half_open()

        if self._state == State.OPEN:
            self._metrics.total_rejections += 1
            elapsed = time.monotonic() - self._opened_at
            retry_after = max(0.0, self.config.reset_timeout_s - elapsed)
            raise CircuitOpenError(self.config.name, retry_after)

        if self._state == State.HALF_OPEN:
            if self._metrics.probe_count >= self.config.probe_limit:
                # Too many probes — force back to OPEN
                self._trip_open()
                self._metrics.total_rejections += 1
                raise CircuitOpenError(self.config.name, self.config.reset_timeout_s)
            self._metrics.probe_count += 1

        self._metrics.total_calls += 1
        try:
            result: T = fn()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def reset(self) -> None:
        """Manually force the circuit to CLOSED state (e.g., for testing)."""
        self._state = State.CLOSED
        self._metrics = _Metrics()
        self._opened_at = 0.0

    def force_open(self) -> None:
        """Manually force the circuit to OPEN state."""
        self._trip_open()

    def snapshot(self) -> dict[str, object]:
        """Return a serialisable snapshot of current state and metrics."""
        m = self._metrics
        return {
            "name": self.config.name,
            "state": self._state.value,
            "consecutive_failures": m.consecutive_failures,
            "consecutive_successes": m.consecutive_successes,
            "total_calls": m.total_calls,
            "total_failures": m.total_failures,
            "total_rejections": m.total_rejections,
            "probe_count": m.probe_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        self._metrics.consecutive_failures = 0
        if self._state == State.HALF_OPEN:
            self._metrics.consecutive_successes += 1
            if self._metrics.consecutive_successes >= self.config.success_threshold:
                self._close()
        else:
            self._metrics.consecutive_successes = 0

    def _on_failure(self) -> None:
        self._metrics.total_failures += 1
        self._metrics.consecutive_successes = 0
        if self._state == State.HALF_OPEN:
            # Any failure in HALF_OPEN trips back to OPEN
            self._trip_open()
        else:
            self._metrics.consecutive_failures += 1
            if self._metrics.consecutive_failures >= self.config.failure_threshold:
                self._trip_open()

    def _trip_open(self) -> None:
        self._state = State.OPEN
        self._opened_at = time.monotonic()
        self._metrics.consecutive_failures = 0
        self._metrics.consecutive_successes = 0
        self._metrics.probe_count = 0

    def _close(self) -> None:
        self._state = State.CLOSED
        self._metrics.consecutive_failures = 0
        self._metrics.consecutive_successes = 0
        self._metrics.probe_count = 0

    def _maybe_transition_to_half_open(self) -> None:
        if self._state == State.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.reset_timeout_s:
                self._state = State.HALF_OPEN
                self._metrics.probe_count = 0
                self._metrics.consecutive_successes = 0
