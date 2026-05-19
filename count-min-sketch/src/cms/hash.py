"""Pairwise-independent hash family for Count-Min sketch.

CMS needs ``depth`` independent hash functions ``h_i(x) → [0, width)``.
We derive them from a single deterministic hash by varying a seed
byte fed into BLAKE2b's `person` parameter — this gives a family
of distinct deterministic hashes without re-implementing
multiplicative-shift / tabulation / etc.

Concretely:

* ``hash64(value, seed=i)`` returns the lower 8 bytes of
  ``BLAKE2b(value, person=f"cms-seed-{i}")``.
* ``index_for(value, seed, width) = hash64(value, seed) % width``.

The seed-vs-data domain separation guarantees independence
between rows: even if two values collide in row 0 they're unlikely
to collide in row 1 (since the hash inputs differ in their
``person`` parameter).
"""

from __future__ import annotations

import hashlib

_PERSONALITY_PREFIX = b"cms-seed-"


def hash64(value: str | bytes | int | float, seed: int = 0) -> int:
    """Return a deterministic 64-bit hash of ``value`` for a given ``seed``."""
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = str(value).encode("utf-8")
    # BLAKE2b ``person`` parameter is bounded to 16 bytes max.
    person = (_PERSONALITY_PREFIX + str(seed).encode("ascii"))[:16]
    digest = hashlib.blake2b(data, digest_size=8, person=person).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def index_for(value: str | bytes | int | float, seed: int, width: int) -> int:
    """Bucket index in row ``seed`` for ``value``, in ``[0, width)``."""
    if width <= 0:
        raise ValueError(f"width must be > 0, got {width}")
    return hash64(value, seed=seed) % width


__all__ = ["hash64", "index_for"]
