"""Simulate failure patterns against a circuit breaker."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from circuitbreaker.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError, State


@dataclass
class SimResult:
    """Result of a simulation run."""

    total_calls: int
    successful_calls: int
    failed_calls: int
    rejected_calls: int
    state_transitions: list[str]
    final_state: State


def simulate(
    failure_rate: float = 0.6,
    n_calls: int = 50,
    failure_threshold: int = 3,
    reset_timeout_s: float = 0.01,  # short for fast simulation
    success_threshold: int = 2,
    seed: int = 42,
) -> SimResult:
    """Simulate a pattern of successes and failures through a circuit breaker.

    Args:
        failure_rate:       Probability each call fails (0.0-1.0).
        n_calls:            Number of calls to attempt.
        failure_threshold:  Circuit trips OPEN after this many consecutive failures.
        reset_timeout_s:    Time in OPEN before moving to HALF_OPEN.
        success_threshold:  Successes needed in HALF_OPEN to close.
        seed:               RNG seed.
    """
    rng = random.Random(seed)
    cfg = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        reset_timeout_s=reset_timeout_s,
        success_threshold=success_threshold,
    )
    cb = CircuitBreaker(config=cfg)

    successful = 0
    failed = 0
    rejected = 0
    prev_state = cb.state
    transitions: list[str] = [f"start:{prev_state.value}"]

    for _ in range(n_calls):
        # Track state changes
        cur_state = cb.state
        if cur_state != prev_state:
            transitions.append(f"{prev_state.value}->{cur_state.value}")
            prev_state = cur_state

        should_fail = rng.random() < failure_rate

        def _call(sf: bool = should_fail) -> str:
            if sf:
                raise RuntimeError("simulated failure")
            return "ok"

        try:
            cb.call(_call)
            successful += 1
        except CircuitOpenError:
            rejected += 1
            # Brief sleep to allow timeout
            time.sleep(reset_timeout_s * 0.5)
        except RuntimeError:
            failed += 1

    return SimResult(
        total_calls=n_calls,
        successful_calls=successful,
        failed_calls=failed,
        rejected_calls=rejected,
        state_transitions=transitions,
        final_state=cb.state,
    )
