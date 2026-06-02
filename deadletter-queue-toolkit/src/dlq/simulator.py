"""Deterministic dead-letter generator."""

from __future__ import annotations

import random

from dlq.schema import DeadLetter, classify

# Sample error messages keyed loosely by what would actually classify
# to each bucket — fed through ``classify`` to verify roundtrip.
_ERRORS: tuple[tuple[str, str], ...] = (
    ("orders", "schema mismatch: missing field 'customer_id'"),
    ("orders", "decode error: truncated JSON at offset 1024"),
    ("payments", "429 Too Many Requests: rate limit exceeded"),
    ("payments", "throttled by downstream gateway"),
    ("inventory", "Connection refused: postgres:5432"),
    ("inventory", "503 Service Unavailable"),
    ("audit", "Operation timed out after 30s"),
    ("audit", "deadline exceeded"),
    ("metrics", "Unknown signal: SIGUSR2"),  # falls through to UNKNOWN
)


def generate(n: int = 50, seed: int = 0) -> list[DeadLetter]:
    """Generate ``n`` synthetic dead letters spanning all failure kinds."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    out: list[DeadLetter] = []
    for i in range(n):
        topic, err = rng.choice(_ERRORS)
        first = rng.randint(1_700_000_000_000, 1_800_000_000_000)
        retries = rng.randint(1, 8)
        out.append(
            DeadLetter(
                message_id=f"m-{i:06d}",
                payload=f'{{"i":{i}}}',
                original_topic=topic,
                failure_kind=classify(err),
                error_message=err,
                retry_count=retries,
                first_failed_at_ms=first,
                last_failed_at_ms=first + retries * 1_000,
                headers={"source": "synthetic", "seed": str(seed)},
            )
        )
    return out


__all__ = ["generate"]
