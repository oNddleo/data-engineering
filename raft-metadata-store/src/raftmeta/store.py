"""High-level metadata store API on top of the Raft cluster."""

from __future__ import annotations

from raftmeta.cluster import RaftCluster


class MetadataStore:
    """Linearisable KV metadata store backed by a Raft cluster.

    All writes go through the Raft leader and are replicated before
    the call returns. Reads are served from the leader's committed state.
    """

    def __init__(
        self,
        node_ids: list[str] | None = None,
        seed: int | None = None,
        replicate_ticks: int = 500,
    ) -> None:
        ids = node_ids or ["n0", "n1", "n2"]
        self._cluster = RaftCluster(node_ids=ids, seed=seed)
        self._replicate_ticks = replicate_ticks
        # Bootstrap: let the cluster elect a leader
        self._cluster.run_until_leader(max_ticks=2000)

    # ── KV operations ─────────────────────────────────────────────────────────

    def set(self, key: str, value: str) -> bool:
        """Write a key-value pair. Returns True on success."""
        ok = self._cluster.write(f"SET {key} {value}")
        if ok:
            self._cluster.replicate(self._replicate_ticks)
        return ok

    def get(self, key: str) -> str | None:
        """Read a key from the committed store."""
        return self._cluster.read(key)

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the command was accepted."""
        ok = self._cluster.write(f"DEL {key}")
        if ok:
            self._cluster.replicate(self._replicate_ticks)
        return ok

    # ── Cluster introspection ─────────────────────────────────────────────────

    @property
    def leader(self) -> str | None:
        return self._cluster.leader()

    @property
    def cluster(self) -> RaftCluster:
        return self._cluster

    def keys(self) -> list[str]:
        ldr = self._cluster.leader()
        if ldr is None:
            return []
        return list(self._cluster.nodes[ldr].kv.keys())
