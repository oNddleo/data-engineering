"""Token Bucket rate limiter.

The token bucket accumulates tokens at a constant rate (refill_rate tokens/sec)
up to a maximum capacity. Each request consumes one or more tokens.
Bursts are absorbed as long as tokens remain.

Clock is injectable for deterministic testing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class RateLimitExceeded(Exception):
    """Raised when the rate limit is exceeded and wait is not requested."""

    def __init__(self, name: str, tokens_needed: int, tokens_available: float) -> None:
        self.name = name
        self.tokens_needed = tokens_needed
        self.tokens_available = tokens_available
        super().__init__(
            f"Rate limit '{name}': need {tokens_needed} tokens, "
            f"only {tokens_available:.2f} available"
        )


@dataclass
class TokenBucket:
    """Token bucket rate limiter.

    Args:
        capacity:       Maximum tokens the bucket can hold (burst size).
        refill_rate:    Tokens added per second.
        name:           Human-readable label.
        _clock:         Callable returning current time in seconds (injectable).
    """

    capacity: float
    refill_rate: float
    name: str = "default"
    _clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    _tokens: float = field(init=False)
    _last_refill: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")
        self._tokens = self.capacity
        self._last_refill = self._clock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tokens(self) -> float:
        """Current token count after refill."""
        self._refill()
        return self._tokens

    def acquire(self, n: int = 1) -> bool:
        """Try to consume *n* tokens.

        Returns:
            True if tokens were consumed, False if not enough tokens.
        """
        if n < 1:
            raise ValueError("n must be >= 1")
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def acquire_or_raise(self, n: int = 1) -> None:
        """Consume *n* tokens or raise RateLimitExceeded."""
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
        else:
            raise RateLimitExceeded(self.name, n, self._tokens)

    def time_to_tokens(self, n: int = 1) -> float:
        """Seconds to wait until *n* tokens are available (0 if already available)."""
        self._refill()
        if self._tokens >= n:
            return 0.0
        deficit = n - self._tokens
        return deficit / self.refill_rate

    def snapshot(self) -> dict[str, object]:
        """Serialisable snapshot."""
        self._refill()
        return {
            "name": self.name,
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "tokens": round(self._tokens, 6),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now
