"""Consistent-hash ring with virtual nodes.

The classic Karger / Lewin / Lehman / Levine / Panigrahy construction:

* Place each node on a 64-bit ring at **multiple** positions (virtual
  nodes / replicas). More replicas → better balance.
* To find the node for a key, hash the key to its ring position, then
  walk clockwise to the next node.

Properties:

* Adding or removing a node moves only ~``1/N`` of the keys (the keys
  whose closest clockwise node changed) — not all of them, as with
  ``hash mod N``.
* With ``v`` virtual nodes per real node, balance variance is
  ``O(1/√v)`` — 100–200 virtual nodes typically gives good balance.

Implementation:

* Ring is a sorted list of ``(position, node_id)`` pairs.
* Lookup is O(log V) via ``bisect`` where V = ``len(nodes) × replicas``.
"""

from __future__ import annotations

import bisect
import hashlib


def _hash64(s: str) -> int:
    return int.from_bytes(
        hashlib.sha256(s.encode("utf-8")).digest()[:8],
        "big",
    )


class ConsistentHashRing:
    """Mutable consistent-hash ring with virtual-node replication."""

    __slots__ = ("replicas", "_ring_positions", "_ring_nodes", "_nodes")

    def __init__(self, nodes: list[str] | None = None, *, replicas: int = 128) -> None:
        if replicas < 1:
            raise ValueError("replicas must be >= 1")
        self.replicas = replicas
        # Parallel arrays kept sorted by position. Using two lists +
        # bisect is faster than maintaining a dict + sorted-keys list.
        self._ring_positions: list[int] = []
        self._ring_nodes: list[str] = []
        self._nodes: set[str] = set()
        for n in nodes or []:
            self.add_node(n)

    # ----- mutation ------------------------------------------------------

    def add_node(self, node: str) -> None:
        if not node:
            raise ValueError("node id must be non-empty")
        if node in self._nodes:
            return
        self._nodes.add(node)
        for v in range(self.replicas):
            pos = _hash64(f"{node}#{v}")
            idx = bisect.bisect_left(self._ring_positions, pos)
            self._ring_positions.insert(idx, pos)
            self._ring_nodes.insert(idx, node)

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            return
        self._nodes.remove(node)
        # Filter out all entries owned by ``node`` (replicas have the same
        # node_id but different positions).
        kept = [
            (p, n) for p, n in zip(self._ring_positions, self._ring_nodes, strict=True) if n != node
        ]
        self._ring_positions = [p for p, _ in kept]
        self._ring_nodes = [n for _, n in kept]

    # ----- lookup --------------------------------------------------------

    def node_for(self, key: str) -> str:
        """Return the node id that owns ``key``."""
        if not self._ring_positions:
            raise RuntimeError("ring is empty — add at least one node")
        pos = _hash64(key)
        idx = bisect.bisect_right(self._ring_positions, pos) % len(self._ring_positions)
        return self._ring_nodes[idx]

    # ----- introspection -------------------------------------------------

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)

    @property
    def n_virtual(self) -> int:
        return len(self._ring_positions)


__all__ = ["ConsistentHashRing"]
