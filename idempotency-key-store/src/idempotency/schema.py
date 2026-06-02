"""Idempotency-key entry schema.

When a client retries a write due to a network blip, the server must
not duplicate the side effect. Idempotency keys solve this:

1. Client sends a request with an ``Idempotency-Key`` header.
2. Server checks the store. If the key exists and has the same
   request fingerprint, replay the cached response (no side effect).
3. If the key exists but the request fingerprint differs, reject
   the request (key reused for a different payload — usually a client
   bug or attack).
4. If the key is new, execute the operation, then store the
   ``(key, fingerprint, response, status, expires_at)`` tuple.

Entries expire after a TTL (typical: 24 hours). The TTL must be
longer than the longest plausible client retry window.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


class EntryStatus(str, Enum):
    """Lifecycle state of an entry."""

    IN_PROGRESS = "in_progress"  # operation started, not yet committed
    SUCCEEDED = "succeeded"  # final response cached
    FAILED = "failed"  # operation failed — should retry give a new key


@dataclass(frozen=True, slots=True)
class IdempotencyEntry:
    """One row in the store."""

    key: str
    request_fingerprint: str  # hash of the request body / params
    status: EntryStatus
    response_body: str  # cached response (empty for IN_PROGRESS)
    created_at_ms: int
    expires_at_ms: int

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key must be non-empty")
        if not self.request_fingerprint:
            raise ValueError("request_fingerprint must be non-empty")
        if self.created_at_ms < 0:
            raise ValueError("created_at_ms must be >= 0")
        if self.expires_at_ms <= self.created_at_ms:
            raise ValueError("expires_at_ms must be > created_at_ms")
        if self.status == EntryStatus.IN_PROGRESS and self.response_body:
            raise ValueError("IN_PROGRESS entries must have empty response_body")


def fingerprint(payload: str) -> str:
    """Stable SHA-256 fingerprint of a request payload (hex, first 16 chars).

    Production usage should canonicalise JSON before fingerprinting so
    that key reordering doesn't produce different fingerprints. We use
    raw ``payload.encode("utf-8")`` here — the caller is responsible.
    """
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


__all__ = ["EntryStatus", "IdempotencyEntry", "fingerprint"]
