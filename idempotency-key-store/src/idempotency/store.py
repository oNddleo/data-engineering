"""In-memory idempotency store with TTL eviction.

This is a reference implementation — production usage should plug into
Redis (with PEXPIRE), DynamoDB (with TTL attribute), or Postgres
(with a partial index on ``expires_at > now()``).

The store API is built around three operations:

* ``check_or_reserve(key, fingerprint, now_ms, ttl_ms)`` — atomically
  check whether a key exists and, if not, reserve it as IN_PROGRESS.
* ``finalize(key, response_body, status, now_ms)`` — commit the
  result of an operation.
* ``get(key, now_ms)`` — read-only lookup honouring TTL.

The ``Outcome`` enum tells the caller what to do next.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from idempotency.schema import EntryStatus, IdempotencyEntry


class Outcome(str, Enum):
    """Result of ``check_or_reserve``."""

    NEW = "new"  # caller should run the op
    REPLAY_SUCCESS = "replay_success"  # return cached SUCCEEDED response
    REPLAY_FAILED = "replay_failed"  # cached FAILED — caller decides
    IN_PROGRESS = "in_progress"  # another worker is running it
    CONFLICT = "conflict"  # same key, different payload


@dataclass(frozen=True, slots=True)
class ReserveResult:
    outcome: Outcome
    entry: IdempotencyEntry | None


class IdempotencyStore:
    """In-memory store. **Not thread-safe** — wrap if needed."""

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: dict[str, IdempotencyEntry] = {}

    # ----- core operations ----------------------------------------------

    def check_or_reserve(
        self,
        key: str,
        request_fingerprint: str,
        now_ms: int,
        ttl_ms: int = 24 * 3600 * 1000,
    ) -> ReserveResult:
        """Atomically check for an existing entry and reserve if absent.

        Returns the ``Outcome`` the caller should act on:

        * ``NEW`` — no existing entry; we just reserved it as IN_PROGRESS.
          Caller must call ``finalize`` after running the operation.
        * ``REPLAY_SUCCESS`` / ``REPLAY_FAILED`` — existing entry with
          matching fingerprint; caller returns the cached response.
        * ``IN_PROGRESS`` — existing entry is still mid-flight; caller
          typically returns a 409 or polls.
        * ``CONFLICT`` — existing entry has a different fingerprint;
          caller returns 422.
        """
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        existing = self._get_live(key, now_ms)
        if existing is None:
            entry = IdempotencyEntry(
                key=key,
                request_fingerprint=request_fingerprint,
                status=EntryStatus.IN_PROGRESS,
                response_body="",
                created_at_ms=now_ms,
                expires_at_ms=now_ms + ttl_ms,
            )
            self._entries[key] = entry
            return ReserveResult(outcome=Outcome.NEW, entry=entry)

        if existing.request_fingerprint != request_fingerprint:
            return ReserveResult(outcome=Outcome.CONFLICT, entry=existing)

        if existing.status == EntryStatus.IN_PROGRESS:
            return ReserveResult(outcome=Outcome.IN_PROGRESS, entry=existing)
        if existing.status == EntryStatus.SUCCEEDED:
            return ReserveResult(outcome=Outcome.REPLAY_SUCCESS, entry=existing)
        return ReserveResult(outcome=Outcome.REPLAY_FAILED, entry=existing)

    def finalize(
        self,
        key: str,
        response_body: str,
        status: EntryStatus,
        now_ms: int,
    ) -> IdempotencyEntry:
        """Commit a completed operation."""
        if status == EntryStatus.IN_PROGRESS:
            raise ValueError("cannot finalize as IN_PROGRESS")
        existing = self._entries.get(key)
        if existing is None:
            raise KeyError(f"no reservation for key {key!r}")
        # Preserve the expires_at from the reservation so the TTL
        # window matches the client's retry window.
        new_entry = IdempotencyEntry(
            key=key,
            request_fingerprint=existing.request_fingerprint,
            status=status,
            response_body=response_body if status == EntryStatus.SUCCEEDED else "",
            created_at_ms=existing.created_at_ms,
            expires_at_ms=existing.expires_at_ms,
        )
        self._entries[key] = new_entry
        _ = now_ms  # accepted for API symmetry; not used in this in-mem impl
        return new_entry

    def get(self, key: str, now_ms: int) -> IdempotencyEntry | None:
        """Read-only lookup respecting TTL."""
        return self._get_live(key, now_ms)

    def evict_expired(self, now_ms: int) -> int:
        """Remove all expired entries; return count evicted."""
        expired = [k for k, e in self._entries.items() if e.expires_at_ms <= now_ms]
        for k in expired:
            del self._entries[k]
        return len(expired)

    # ----- introspection -------------------------------------------------

    def __len__(self) -> int:
        return len(self._entries)

    # ----- internals -----------------------------------------------------

    def _get_live(self, key: str, now_ms: int) -> IdempotencyEntry | None:
        e = self._entries.get(key)
        if e is None:
            return None
        if e.expires_at_ms <= now_ms:
            # Lazy eviction.
            del self._entries[key]
            return None
        return e


__all__ = ["IdempotencyStore", "Outcome", "ReserveResult"]
