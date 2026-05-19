"""Multi-seed BLAKE2b hash family for Bloom filters.

A Bloom filter needs ``k`` *independent* hash functions
``h_0..h_{k-1}: V → [0, m)``. We derive them from a single
deterministic primitive by feeding distinct values into BLAKE2b's
``person`` parameter (a 16-byte personalization slot).

Why BLAKE2b instead of e.g. ``hash(...)``:

* Deterministic across processes (CPython's ``hash`` randomises strings).
* Independent rows — the ``person`` byte sequence guarantees that
  ``h_i`` and ``h_j`` are unrelated even when applied to the same
  input.
* No external dependency — ``hashlib.blake2b`` is stdlib.

This is the same family used in our Count-Min-Sketch package (#48).
"""

from __future__ import annotations

import hashlib

_PERSONALITY_PREFIX = b"bloom-seed-"


def hash64(value: str | bytes | int | float, seed: int = 0) -> int:
    """Return a deterministic 64-bit hash of ``value`` for ``seed``."""
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = str(value).encode("utf-8")
    person = (_PERSONALITY_PREFIX + str(seed).encode("ascii"))[:16]
    digest = hashlib.blake2b(data, digest_size=8, person=person).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def positions(
    value: str | bytes | int | float,
    n_hashes: int,
    size_bits: int,
) -> list[int]:
    """Compute the ``n_hashes`` bit positions for ``value`` in ``[0, size_bits)``."""
    if n_hashes < 1:
        raise ValueError(f"n_hashes must be >= 1, got {n_hashes}")
    if size_bits < 1:
        raise ValueError(f"size_bits must be >= 1, got {size_bits}")
    return [hash64(value, seed=i) % size_bits for i in range(n_hashes)]


__all__ = ["hash64", "positions"]
