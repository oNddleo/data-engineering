"""PBFT consensus state machine for watermark advancement.

Each replica runs one PBFTConsensus instance per (view, seq) slot.
Only the primary sends PRE-PREPARE; all honest replicas broadcast PREPARE
and then COMMIT once the prepared certificate is acquired.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from bftstream.schema import BFTMessage, MessageType, WatermarkProposal


def _proposal_digest(proposal: WatermarkProposal) -> int:
    return hash((proposal.window_id, proposal.record_count, proposal.checksum))


@dataclass
class PBFTSlot:
    """State for a single (view, seq) consensus instance."""

    view: int
    seq: int
    proposal: WatermarkProposal | None = field(default=None)
    prepares: dict[str, int] = field(default_factory=dict)  # sender → digest
    commits: dict[str, int] = field(default_factory=dict)  # sender → digest
    prepared: bool = field(default=False)
    committed_local: bool = field(default=False)


class PBFTConsensus:
    """Per-replica PBFT engine.

    The replica drives the protocol by calling:
    - ``pre_prepare(proposal)`` when it is the primary for the current view.
    - ``receive(msg)`` for every inbound PBFT message.
    - ``drain_outbox()`` after each round to collect messages to send.

    Committed watermarks are accessible via ``committed``.
    """

    def __init__(self, replica_id: str, peers: list[str], f: int) -> None:
        self.replica_id = replica_id
        self.peers = peers
        self.f = f  # max Byzantine nodes tolerated
        self._quorum = 2 * f + 1  # 2f+1 for prepare/commit certificates
        self._slots: dict[tuple[int, int], PBFTSlot] = {}
        self._view = 0
        self._seq = 0
        self.outbox: deque[BFTMessage] = deque()
        self.committed: list[WatermarkProposal] = []

    # ── Primary path ─────────────────────────────────────────────────────────

    def pre_prepare(self, proposal: WatermarkProposal) -> None:
        """Called by the current primary to initiate consensus."""
        self._seq += 1
        seq = self._seq
        digest = _proposal_digest(proposal)
        slot = PBFTSlot(view=self._view, seq=seq, proposal=proposal)
        # Primary adds its own PREPARE to the slot immediately
        slot.prepares[self.replica_id] = digest
        self._slots[(self._view, seq)] = slot
        for peer in self.peers:
            self.outbox.append(
                BFTMessage(
                    type=MessageType.PRE_PREPARE,
                    sender=self.replica_id,
                    receiver=peer,
                    view=self._view,
                    seq=seq,
                    proposal=proposal,
                    digest=digest,
                )
            )
        # Primary also participates in PREPARE phase (standard PBFT)
        for peer in self.peers:
            self.outbox.append(
                BFTMessage(
                    type=MessageType.PREPARE,
                    sender=self.replica_id,
                    receiver=peer,
                    view=self._view,
                    seq=seq,
                    digest=digest,
                )
            )

    # ── Message handling ─────────────────────────────────────────────────────

    def receive(self, msg: BFTMessage) -> None:
        if msg.view != self._view:
            return
        if msg.type == MessageType.PRE_PREPARE:
            self._handle_pre_prepare(msg)
        elif msg.type == MessageType.PREPARE:
            self._handle_prepare(msg)
        elif msg.type == MessageType.COMMIT:
            self._handle_commit(msg)

    def _handle_pre_prepare(self, msg: BFTMessage) -> None:
        if msg.proposal is None:
            return
        key = (msg.view, msg.seq)
        if key in self._slots:
            return  # already seen
        # Validate: non-decreasing watermark, correct digest
        if msg.digest != _proposal_digest(msg.proposal):
            return  # corrupt message
        slot = PBFTSlot(view=msg.view, seq=msg.seq, proposal=msg.proposal)
        # Add our own PREPARE to the slot immediately
        slot.prepares[self.replica_id] = msg.digest
        self._slots[key] = slot
        # Broadcast PREPARE to all peers
        for peer in self.peers:
            self.outbox.append(
                BFTMessage(
                    type=MessageType.PREPARE,
                    sender=self.replica_id,
                    receiver=peer,
                    view=msg.view,
                    seq=msg.seq,
                    digest=msg.digest,
                )
            )

    def _handle_prepare(self, msg: BFTMessage) -> None:
        key = (msg.view, msg.seq)
        slot = self._slots.get(key)
        if slot is None or slot.proposal is None:
            return
        if msg.digest != _proposal_digest(slot.proposal):
            return  # mismatched digest — Byzantine
        slot.prepares[msg.sender] = msg.digest
        if not slot.prepared and len(slot.prepares) >= self._quorum:
            slot.prepared = True
            # Enter COMMIT phase
            commit_digest = msg.digest
            slot.commits[self.replica_id] = commit_digest
            for peer in self.peers:
                self.outbox.append(
                    BFTMessage(
                        type=MessageType.COMMIT,
                        sender=self.replica_id,
                        receiver=peer,
                        view=msg.view,
                        seq=msg.seq,
                        digest=commit_digest,
                    )
                )

    def _handle_commit(self, msg: BFTMessage) -> None:
        key = (msg.view, msg.seq)
        slot = self._slots.get(key)
        if slot is None or slot.proposal is None:
            return
        if msg.digest != _proposal_digest(slot.proposal):
            return
        slot.commits[msg.sender] = msg.digest
        if not slot.committed_local and len(slot.commits) >= self._quorum:
            slot.committed_local = True
            self.committed.append(slot.proposal)

    # ── View ─────────────────────────────────────────────────────────────────

    def current_view(self) -> int:
        return self._view
