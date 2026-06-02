"""Unit tests for the PBFT consensus engine."""

from __future__ import annotations

from bftstream.pbft import PBFTConsensus
from bftstream.schema import BFTMessage, MessageType, WatermarkProposal


def _proposal(wid: int = 0, count: int = 10, csum: int = 12345) -> WatermarkProposal:
    return WatermarkProposal(
        view=0,
        seq=0,
        window_id=wid,
        record_count=count,
        checksum=csum,
        proposer_id="r0",
    )


def _cluster(n: int, f: int) -> dict[str, PBFTConsensus]:
    ids = [f"r{i}" for i in range(n)]
    return {rid: PBFTConsensus(rid, [p for p in ids if p != rid], f) for rid in ids}


class TestPBFTConsensus:
    def test_primary_sends_pre_prepares(self) -> None:
        nodes = _cluster(4, 1)
        primary = nodes["r0"]
        primary.pre_prepare(_proposal())
        # Primary sends PRE-PREPARE + PREPARE to each of 3 peers
        assert len(primary.outbox) == 6

    def test_primary_outbox_has_pre_prepares_and_prepares(self) -> None:
        nodes = _cluster(4, 1)
        nodes["r0"].pre_prepare(_proposal())
        msgs = list(nodes["r0"].outbox)
        types = {m.type for m in msgs}
        assert MessageType.PRE_PREPARE in types
        assert MessageType.PREPARE in types

    def test_follower_responds_with_prepare(self) -> None:
        nodes = _cluster(4, 1)
        nodes["r0"].pre_prepare(_proposal())
        # Deliver PRE-PREPARE to r1
        for msg in list(nodes["r0"].outbox):
            if msg.receiver == "r1":
                nodes["r1"].receive(msg)
        prepares = [m for m in nodes["r1"].outbox if m.type == MessageType.PREPARE]
        assert len(prepares) == 3  # sent to all peers

    def test_commit_after_quorum_prepares(self) -> None:
        """Full 4-node (f=1) protocol should reach commit on r0."""
        n, f = 4, 1
        nodes = _cluster(n, f)
        primary = nodes["r0"]
        proposal = _proposal()
        primary.pre_prepare(proposal)

        # Deliver PRE-PREPARE from r0 to r1, r2, r3
        round1 = list(primary.outbox)
        primary.outbox.clear()
        for msg in round1:
            nodes[msg.receiver].receive(msg)

        # Collect PREPARE messages and deliver to all
        round2: list[BFTMessage] = []
        for node in nodes.values():
            round2.extend(node.outbox)
            node.outbox.clear()
        for msg in round2:
            if msg.type == MessageType.PREPARE:
                nodes[msg.receiver].receive(msg)

        # Collect COMMIT messages and deliver to all
        round3: list[BFTMessage] = []
        for node in nodes.values():
            round3.extend(node.outbox)
            node.outbox.clear()
        for msg in round3:
            if msg.type == MessageType.COMMIT:
                nodes[msg.receiver].receive(msg)

        # At least quorum (3) replicas should have committed
        committed_count = sum(1 for nd in nodes.values() if nd.committed)
        assert committed_count >= 3

    def test_wrong_digest_ignored(self) -> None:
        nodes = _cluster(4, 1)
        # Build a corrupted PRE-PREPARE
        bad_msg = BFTMessage(
            type=MessageType.PRE_PREPARE,
            sender="r0",
            receiver="r1",
            view=0,
            seq=1,
            proposal=_proposal(csum=99999),
            digest=0xDEADBEEF,  # wrong digest
        )
        nodes["r1"].receive(bad_msg)
        # r1 should not have added slot (corrupt message ignored)
        assert len(nodes["r1"].committed) == 0
        assert len(nodes["r1"].outbox) == 0

    def test_no_commit_without_quorum(self) -> None:
        """With only 1 prepare received, node should not commit (f=1 needs 3)."""
        nodes = _cluster(4, 1)
        primary = nodes["r0"]
        primary.pre_prepare(_proposal())
        # Deliver only to r1
        for msg in list(primary.outbox):
            if msg.receiver == "r1":
                primary.outbox.remove(msg)
                nodes["r1"].receive(msg)
                break
        # r1 has one PREPARE from itself only → no commit
        assert len(nodes["r1"].committed) == 0

    def test_reset_view(self) -> None:
        nodes = _cluster(4, 1)
        assert nodes["r0"].current_view() == 0
