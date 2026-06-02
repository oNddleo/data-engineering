"""Simulated Raft cluster — routes messages between nodes synchronously."""

from __future__ import annotations

import random

from raftmeta.node import RaftNode
from raftmeta.schema import NodeState


class RaftCluster:
    """In-process Raft cluster for deterministic simulation and testing."""

    def __init__(
        self,
        node_ids: list[str],
        seed: int | None = None,
    ) -> None:
        # Derive distinct per-node seeds so nodes have staggered election timeouts.
        # Using the same seed for all nodes causes simultaneous timeouts → split votes.
        rng = random.Random(seed)
        peers_map = {nid: [p for p in node_ids if p != nid] for nid in node_ids}
        self.nodes: dict[str, RaftNode] = {
            nid: RaftNode(nid, peers_map[nid], seed=rng.randint(0, 2**31)) for nid in node_ids
        }
        self._partitioned: set[str] = set()  # nodes cut off from the cluster

    # ── Routing ────────────────────────────────────────────────────────────────

    def _deliver_messages(self) -> int:
        """Drain outboxes and deliver to target nodes. Returns message count."""
        count = 0
        for node in self.nodes.values():
            while node.outbox:
                msg = node.outbox.popleft()
                target = self.nodes.get(msg.receiver)
                if target is None:
                    continue
                # Drop if either sender or receiver is partitioned
                if msg.sender in self._partitioned or msg.receiver in self._partitioned:
                    continue
                target.receive(msg)
                count += 1
        return count

    # ── Ticking ────────────────────────────────────────────────────────────────

    def tick(self, n: int = 1) -> None:
        """Advance all non-partitioned nodes by ``n`` ticks, flushing messages after each."""
        for _ in range(n):
            for node in self.nodes.values():
                if node.node_id not in self._partitioned:
                    node.tick()
            self._deliver_messages()

    def run_until_leader(self, max_ticks: int = 2000) -> str | None:
        """Tick until a stable leader emerges. Returns leader id or None."""
        for _ in range(max_ticks):
            self.tick()
            leader = self.leader()
            if leader is not None:
                return leader
        return None

    # ── Queries ────────────────────────────────────────────────────────────────

    def leader(self) -> str | None:
        """Return the current leader node id, if exactly one leader exists."""
        leaders = [
            nid
            for nid, n in self.nodes.items()
            if n.state == NodeState.LEADER and nid not in self._partitioned
        ]
        return leaders[0] if len(leaders) == 1 else None

    def node(self, node_id: str) -> RaftNode:
        return self.nodes[node_id]

    # ── Fault injection ────────────────────────────────────────────────────────

    def partition(self, node_id: str) -> None:
        """Isolate a node from the cluster (simulated network partition)."""
        self._partitioned.add(node_id)

    def heal(self, node_id: str) -> None:
        """Reconnect a partitioned node."""
        self._partitioned.discard(node_id)

    # ── Client API ─────────────────────────────────────────────────────────────

    def write(self, command: str, client_id: str = "") -> bool:
        """Submit a write command via the current leader."""
        ldr = self.leader()
        if ldr is None:
            return False
        return self.nodes[ldr].client_write(command, client_id)

    def read(self, key: str) -> str | None:
        """Read a key from the current leader."""
        ldr = self.leader()
        if ldr is None:
            return None
        return self.nodes[ldr].client_read(key)

    def replicate(self, max_ticks: int = 500) -> bool:
        """Tick until the latest write is committed and applied on all live nodes."""
        ldr = self.leader()
        if ldr is None:
            return False
        min_commit = len(self.nodes[ldr].log) - 1
        if min_commit < 0:
            return True  # no entries to replicate
        for _ in range(max_ticks):
            self.tick()
            ldr = self.leader()
            if ldr is None:
                continue
            if self.nodes[ldr].commit_index < min_commit:
                continue  # latest write not yet committed
            leader_commit = self.nodes[ldr].commit_index
            all_caught_up = all(
                n.last_applied >= leader_commit
                for nid, n in self.nodes.items()
                if nid not in self._partitioned
            )
            if all_caught_up:
                return True
        return False
