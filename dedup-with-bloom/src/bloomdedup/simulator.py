"""Deterministic synthetic stream generator with controllable duplication."""

from __future__ import annotations

import random


def generate(
    n: int = 10_000,
    n_unique: int = 1_000,
    duplicate_rate: float = 0.5,
    seed: int = 0,
) -> list[str]:
    """Produce a stream of ``n`` keys with controlled duplication.

    Each draw is either a fresh key from the universe (if not yet seen)
    or a repeat of a previously-seen key, with probability
    ``duplicate_rate``. The first record is always fresh.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if n_unique <= 0:
        raise ValueError("n_unique must be > 0")
    if not 0.0 <= duplicate_rate <= 1.0:
        raise ValueError("duplicate_rate must be in [0, 1]")

    rng = random.Random(seed)
    out: list[str] = []
    seen: list[str] = []
    for _ in range(n):
        if seen and rng.random() < duplicate_rate:
            out.append(rng.choice(seen))
        else:
            key = f"k{rng.randrange(n_unique):08d}"
            out.append(key)
            if key not in seen:
                seen.append(key)
    return out


__all__ = ["generate"]
