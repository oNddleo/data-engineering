"""Deterministic key stream generator."""

from __future__ import annotations

import random


def generate_keys(n: int = 1000, alphabet_size: int = 1000, seed: int = 0) -> list[str]:
    """Generate ``n`` keys from a universe of ``alphabet_size`` distinct values."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if alphabet_size <= 0:
        raise ValueError("alphabet_size must be > 0")
    rng = random.Random(seed)
    return [f"k{rng.randrange(alphabet_size):08d}" for _ in range(n)]


__all__ = ["generate_keys"]
