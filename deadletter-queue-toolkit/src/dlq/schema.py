"""DLQ message schema + failure classification.

A DLQ is the safety net for a streaming pipeline: when a consumer
fails to process a message after N retries, the message is parked in
a separate "dead letter" queue for human inspection or out-of-band
replay.

Why messages end up here:

* **Poison**: the payload is permanently malformed (schema mismatch,
  truncated JSON, wrong content-type) — no amount of retry will fix it.
* **Transient**: an upstream dependency is briefly down (DB unreachable,
  rate-limited API). Should retry with backoff.
* **Throttled**: 429 from a downstream — usually retryable.
* **Timeout**: handler exceeded its SLA. Could be transient or poison.
* **Unknown**: we don't have enough signal to classify; treat as
  retryable up to the policy limit.

The classifier turns a free-text error message into one of these
buckets. Production deployments swap this for a custom classifier
that knows their own error grammar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FailureKind(str, Enum):
    POISON = "poison"
    TRANSIENT = "transient"
    THROTTLED = "throttled"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """One message parked in the DLQ."""

    message_id: str
    payload: str  # opaque serialised payload
    original_topic: str  # where the message came from
    failure_kind: FailureKind
    error_message: str
    retry_count: int  # how many attempts before giving up
    first_failed_at_ms: int  # epoch ms of first failure
    last_failed_at_ms: int  # epoch ms of last failure
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id must be non-empty")
        if not self.original_topic:
            raise ValueError("original_topic must be non-empty")
        if self.retry_count < 0:
            raise ValueError("retry_count must be >= 0")
        if self.first_failed_at_ms < 0 or self.last_failed_at_ms < 0:
            raise ValueError("failure timestamps must be >= 0")
        if self.last_failed_at_ms < self.first_failed_at_ms:
            raise ValueError("last_failed_at_ms must be >= first_failed_at_ms")

    @property
    def age_ms(self) -> int:
        """Wall-clock age of the dead letter, in milliseconds."""
        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        return max(0, now_ms - self.first_failed_at_ms)


# Keyword-based classifier. Order matters — earlier rules win.
_POISON_KEYWORDS = ("malformed", "schema mismatch", "decode error", "invalid json", "truncated")
_THROTTLE_KEYWORDS = ("429", "throttled", "rate limit", "too many requests")
_TIMEOUT_KEYWORDS = ("timeout", "timed out", "deadline exceeded")
_TRANSIENT_KEYWORDS = (
    "connection refused",
    "connection reset",
    "503",
    "502",
    "504",
    "unavailable",
    "dns",
)


def classify(error_message: str) -> FailureKind:
    """Bucket a free-text error message into a ``FailureKind``."""
    msg = error_message.lower()
    if any(kw in msg for kw in _POISON_KEYWORDS):
        return FailureKind.POISON
    if any(kw in msg for kw in _THROTTLE_KEYWORDS):
        return FailureKind.THROTTLED
    if any(kw in msg for kw in _TIMEOUT_KEYWORDS):
        return FailureKind.TIMEOUT
    if any(kw in msg for kw in _TRANSIENT_KEYWORDS):
        return FailureKind.TRANSIENT
    return FailureKind.UNKNOWN


__all__ = ["DeadLetter", "FailureKind", "classify"]
