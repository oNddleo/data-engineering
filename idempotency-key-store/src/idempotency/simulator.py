"""Deterministic synthetic request stream generator."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyntheticRequest:
    """A simulated client request with an idempotency key."""

    key: str
    payload: str
    arrived_at_ms: int


def generate(
    n_unique: int = 100,
    n_total: int = 500,
    seed: int = 0,
    base_time_ms: int = 1_700_000_000_000,
) -> list[SyntheticRequest]:
    """Generate ``n_total`` requests using ``n_unique`` distinct keys.

    Repeats (retries) carry the same payload as the original — they're
    simulating network blips.
    """
    if n_unique <= 0:
        raise ValueError("n_unique must be > 0")
    if n_total < 0:
        raise ValueError("n_total must be >= 0")
    rng = random.Random(seed)
    unique_payloads = [f'{{"op":{i}}}' for i in range(n_unique)]
    out: list[SyntheticRequest] = []
    for i in range(n_total):
        k_idx = rng.randrange(n_unique)
        out.append(
            SyntheticRequest(
                key=f"k-{k_idx:08d}",
                payload=unique_payloads[k_idx],
                arrived_at_ms=base_time_ms + i * 100,
            )
        )
    return out


__all__ = ["SyntheticRequest", "generate"]
