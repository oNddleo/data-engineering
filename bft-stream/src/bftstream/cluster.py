"""In-process BFT streaming cluster for deterministic simulation and testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bftstream.replica import BFTReplica

if TYPE_CHECKING:
    from bftstream.schema import StreamRecord, WindowAggregate


class BFTCluster:
    """Manages a set of BFT replicas and routes messages between them."""

    def __init__(self, n_replicas: int, f: int = 1, window_size: int = 10) -> None:
        if n_replicas < 3 * f + 1:
            raise ValueError(f"Need at least 3f+1={3*f+1} replicas for f={f}; got {n_replicas}")
        self.n_replicas = n_replicas
        self.f = f
        self.window_size = window_size

        ids = [f"r{i}" for i in range(n_replicas)]
        peers_map = {rid: [p for p in ids if p != rid] for rid in ids}
        self.replicas: dict[str, BFTReplica] = {
            rid: BFTReplica(rid, peers_map[rid], f, window_size) for rid in ids
        }
        # Replicas that have been turned Byzantine
        self._byzantine: set[str] = set()

    # ── Fault injection ───────────────────────────────────────────────────────

    def make_byzantine(self, replica_id: str) -> None:
        """Turn a replica Byzantine (it will ignore all messages)."""
        self.replicas[replica_id].byzantine = True
        self._byzantine.add(replica_id)

    # ── Record ingestion ──────────────────────────────────────────────────────

    def ingest(self, record: StreamRecord) -> None:
        """Deliver a record to all honest replicas."""
        for replica in self.replicas.values():
            if not replica.byzantine:
                replica.ingest(record)
        self._flush_messages()

    def ingest_batch(self, records: list[StreamRecord]) -> None:
        for record in records:
            self.ingest(record)

    # ── Message routing ───────────────────────────────────────────────────────

    def _flush_messages(self) -> None:
        """Route all queued messages until quiescent."""
        max_rounds = 10
        for _ in range(max_rounds):
            messages = []
            for replica in self.replicas.values():
                while replica.outbox:
                    messages.append(replica.outbox.popleft())
            if not messages:
                break
            for msg in messages:
                target = self.replicas.get(msg.receiver)
                if target is not None and not target.byzantine:
                    target.receive(msg)

    # ── Queries ───────────────────────────────────────────────────────────────

    def committed_windows(self, replica_id: str | None = None) -> list[WindowAggregate]:
        """Return committed windows for the given replica (or first honest one)."""
        if replica_id is not None:
            return self.replicas[replica_id].committed_windows
        for rid, r in self.replicas.items():
            if rid not in self._byzantine:
                return r.committed_windows
        return []

    def watermark(self, replica_id: str | None = None) -> int:
        if replica_id is not None:
            return self.replicas[replica_id].watermark
        for rid, r in self.replicas.items():
            if rid not in self._byzantine:
                return r.watermark
        return -1

    def all_honest_agree(self, window_id: int) -> bool:
        """True if all honest replicas have committed window_id."""
        for rid, r in self.replicas.items():
            if rid not in self._byzantine:
                if not any(w.window_id == window_id for w in r.committed_windows):
                    return False
        return True
