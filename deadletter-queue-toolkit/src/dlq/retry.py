"""Retry policies: fixed, exponential, exponential-with-jitter.

Two production-grade jitter schemes — "full" (uniform [0, backoff]) and
"equal" (backoff/2 + uniform[0, backoff/2]):

* **Full jitter** spreads retries over the widest window, giving the
  best thundering-herd protection. Risk: average backoff is halved,
  so callers might effectively give up sooner than expected.
* **Equal jitter** halves the variance but keeps the **mean** at the
  computed backoff. Good default for "do what I say" retries.

The base backoff curve is ``base × multiplier ^ attempt`` capped at
``max_backoff_ms``. For ``base=100``, ``multiplier=2``, ``max=30_000``
that gives 100, 200, 400, 800, 1600, ..., 30_000, 30_000, ...
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


class JitterMode(str, Enum):
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for a retry strategy."""

    max_attempts: int = 5
    base_ms: int = 100
    multiplier: float = 2.0
    max_backoff_ms: int = 30_000
    jitter: JitterMode = JitterMode.FULL

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_ms < 0:
            raise ValueError("base_ms must be >= 0")
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be >= 1.0")
        if self.max_backoff_ms < self.base_ms:
            raise ValueError("max_backoff_ms must be >= base_ms")


def next_backoff_ms(
    policy: RetryPolicy,
    attempt: int,
    *,
    rng: random.Random | None = None,
) -> int:
    """Compute the next sleep, in milliseconds, before attempt ``attempt``.

    ``attempt`` is 0-indexed: ``attempt=0`` is the first retry (after
    the initial failed try). The caller is responsible for not calling
    ``next_backoff_ms`` past ``max_attempts``.

    Pass an explicit ``rng`` for deterministic testing; default uses a
    fresh ``Random()`` seeded by the OS.
    """
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    rng = rng or random.Random()

    # Compute uncapped exponential backoff. Use float math then cap +
    # round to int.
    raw = policy.base_ms * (policy.multiplier**attempt)
    base = min(int(raw), policy.max_backoff_ms)

    if policy.jitter == JitterMode.NONE:
        return base
    if policy.jitter == JitterMode.FULL:
        return rng.randint(0, base)
    # EQUAL
    half = base // 2
    return half + rng.randint(0, half)


def should_retry(policy: RetryPolicy, attempt: int) -> bool:
    """``True`` if we haven't exhausted ``max_attempts`` yet.

    ``attempt`` is the **count of attempts already made** (1-based);
    so the first call after a failure passes ``attempt=1``.
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    return attempt < policy.max_attempts


__all__ = ["JitterMode", "RetryPolicy", "next_backoff_ms", "should_retry"]
