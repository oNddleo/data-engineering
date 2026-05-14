"""Binary Merkle tree over hex SHA-256 hashes.

We use the same odd-leaf-duplication convention as Bitcoin: at each
level, if the number of nodes is odd, duplicate the last node before
pairing. The root is the lone hash at the top.

Inputs are 64-char hex strings (SHA-256). Internal hashing reads the
hex back into bytes, concatenates left || right, and SHA-256s the
result, then hex-encodes again.

The empty-set root is conventionally ``"0" * 64`` — there's no
ambiguity because the ledger never seals an empty day in practice
(no audit-worthy transactions = nothing to seal).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


EMPTY_ROOT = "0" * 64
"""Conventional root for the empty leaf set."""


def hash_pair(left_hex: str, right_hex: str) -> str:
    """SHA-256 of two concatenated hex-decoded hashes."""
    h = hashlib.sha256()
    h.update(bytes.fromhex(left_hex))
    h.update(bytes.fromhex(right_hex))
    return h.hexdigest()


def merkle_root(leaves: Sequence[str]) -> str:
    """Compute the Merkle root of the given leaf hashes.

    Leaves must each be a 64-char hex SHA-256. Returns
    :data:`EMPTY_ROOT` if no leaves; otherwise reduces the tree
    level-by-level (duplicating the last node on odd levels).
    """
    if not leaves:
        return EMPTY_ROOT
    for leaf in leaves:
        if len(leaf) != 64 or any(c not in "0123456789abcdef" for c in leaf.lower()):
            raise ValueError(f"leaf {leaf!r} is not a 64-char hex string")
    cur: list[str] = list(leaves)
    while len(cur) > 1:
        if len(cur) % 2 == 1:
            cur.append(cur[-1])
        cur = [hash_pair(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)]
    return cur[0]


__all__ = ["EMPTY_ROOT", "hash_pair", "merkle_root"]
