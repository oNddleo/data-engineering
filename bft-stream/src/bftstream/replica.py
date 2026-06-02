"""BFT stream replica — ingests records and runs PBFT watermark consensus."""

from __future__ import annotations

from collections import deque

from bftstream.pbft import PBFTConsensus
from bftstream.schema import (
    BFTMessage,
    ReplicaState,
    StreamRecord,
    WatermarkProposal,
    WindowAggregate,
)


class BFTReplica:
    """A single honest replica in the BFT streaming cluster.

    Replicas:
    1. Ingest records locally into window accumulators.
    2. When a window's expected record count is reached, the primary
       proposes a WatermarkAdvance via PBFT.
    3. All honest replicas commit the watermark once 2f+1 COMMIT messages
       are received, finalising the window aggregate.
    """

    def __init__(
        self,
        replica_id: str,
        peers: list[str],
        f: int,
        window_size: int = 10,
        byzantine: bool = False,
    ) -> None:
        self.replica_id = replica_id
        self.peers = peers
        self.f = f
        self.window_size = window_size
        self.byzantine = byzantine

        self.state = ReplicaState.NORMAL
        self._windows: dict[int, WindowAggregate] = {}
        self._committed_windows: list[WindowAggregate] = []
        self._committed_watermark: int = -1

        all_nodes = sorted([replica_id] + peers)
        self._pbft = PBFTConsensus(replica_id, peers, f)
        self._view = 0
        # Primary for view v = nodes[v % len(nodes)]
        self._all_nodes = all_nodes

        self.outbox: deque[BFTMessage] = deque()

    # ── Record ingestion ──────────────────────────────────────────────────────

    def ingest(self, record: StreamRecord) -> None:
        """Add a record to its window accumulator."""
        if self.byzantine:
            return  # faulty replica does nothing (or could inject bad data)
        wid = record.window_id
        if wid not in self._windows:
            self._windows[wid] = WindowAggregate(window_id=wid)
        self._windows[wid].ingest(record)
        # Check if window is ready to close (reached expected count)
        if self._windows[wid].record_count >= self.window_size and self._is_primary():
            self._propose_watermark(wid)

    def _is_primary(self) -> bool:
        n = len(self._all_nodes)
        if n == 0:
            return False
        return self._all_nodes[self._view % n] == self.replica_id

    def _propose_watermark(self, window_id: int) -> None:
        win = self._windows.get(window_id)
        if win is None or win.committed:
            return
        proposal = WatermarkProposal(
            view=self._view,
            seq=0,  # managed by PBFTConsensus
            window_id=window_id,
            record_count=win.record_count,
            checksum=win.checksum,
            proposer_id=self.replica_id,
        )
        self._pbft.pre_prepare(proposal)
        self._drain_pbft()

    # ── Message routing ───────────────────────────────────────────────────────

    def receive(self, msg: BFTMessage) -> None:
        if self.byzantine:
            return
        self._pbft.receive(msg)
        self._drain_pbft()
        self._apply_committed()

    def _drain_pbft(self) -> None:
        while self._pbft.outbox:
            self.outbox.append(self._pbft.outbox.popleft())

    def _apply_committed(self) -> None:
        for proposal in self._pbft.committed:
            wid = proposal.window_id
            if wid <= self._committed_watermark:
                continue  # already committed (idempotent)
            win = self._windows.get(wid)
            if win is None:
                # Create a placeholder for replicas that may have missed records
                win = WindowAggregate(window_id=wid)
                self._windows[wid] = win
            win.committed = True
            if wid > self._committed_watermark:
                self._committed_watermark = wid
            self._committed_windows.append(win)
        # Reset PBFT committed list to avoid double-applying
        self._pbft.committed = []

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def committed_windows(self) -> list[WindowAggregate]:
        return list(self._committed_windows)

    @property
    def watermark(self) -> int:
        return self._committed_watermark
