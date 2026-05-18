"""Deterministic 64-bit hash.

HyperLogLog needs:

1. **Determinism** — same input → same hash across runs (Python's
   built-in ``hash()`` is randomly salted per-interpreter, no good).
2. **Avalanche** — small changes in input scatter wildly across the
   output bits. Crypto-grade hashes are overkill but they have the
   right uniformity for HLL purposes.

We use the **first 8 bytes of BLAKE2b** — stdlib-only, fast
(< 1 µs per call), deterministic, and uniformly distributed in the
output bits. Cryptographic strength isn't a concern; uniformity is.

For ``add(value)``, the input is coerced to bytes via UTF-8 if
str-typed, else passed through ``str().encode()`` for ints/floats/etc.
"""

from __future__ import annotations

import hashlib


def hash64(value: str | bytes | int | float) -> int:
    """Return a deterministic 64-bit unsigned hash of ``value``."""
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = str(value).encode("utf-8")
    digest = hashlib.blake2b(data, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def leading_zeros_64(x: int, max_zeros: int) -> int:
    """Return the number of leading zeros in ``x`` (1-indexed first-1 position).

    For HLL, we need ``rho(w) = position of leftmost 1-bit + 1`` in a
    bit string of length ``q = 64 - p``. ``max_zeros`` is the maximum
    value we'd report (== q + 1) — beyond that all bits were 0.
    """
    if x == 0:
        return max_zeros
    width = max_zeros - 1  # number of meaningful bits (q)
    # Find position of highest set bit; ``count`` = leading-zeros so far.
    for count, i in enumerate(range(width - 1, -1, -1)):
        if (x >> i) & 1:
            return count + 1
    return max_zeros


__all__ = ["hash64", "leading_zeros_64"]
