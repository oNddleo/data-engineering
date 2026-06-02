from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fpaxos.types import BallotNumber, Message, MessageType, QuorumConfig

if TYPE_CHECKING:
    from fpaxos.transport import InMemoryTransport


class ProposerError(Exception):
    """Raised when a proposer cannot make progress (e.g. insufficient quorum)."""


class Proposer:
    """Single Paxos proposer that drives Phase1 and Phase2.

    A proposer is identified by a unique *proposer_id*.  It increments its
    ballot round on each attempt so that retries always use a strictly higher
    ballot, guaranteeing progress when competing proposers back off.
    """

    def __init__(self, proposer_id: int, transport: InMemoryTransport) -> None:
        self.proposer_id = proposer_id
        self.transport = transport
        self._round = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propose(self, value: Any, quorum_config: QuorumConfig) -> Any:
        """Run a full Paxos round and return the decided value.

        Steps
        -----
        1. Phase 1 — broadcast Prepare to all acceptors, collect Q1 promises.
        2. If any promise carries a previously accepted value, replace *value*
           with the one attached to the highest-ballot promise (safety rule).
        3. Phase 2 — broadcast Accept to all acceptors, collect Q2 acceptances.
        4. Return the decided value.

        Raises ``ProposerError`` if the quorum cannot be satisfied (too many
        nodes dropped or NACKed).
        """
        ballot = self._next_ballot()

        # ---- Phase 1 ------------------------------------------------
        p1_responses = self.transport.broadcast_phase1a(ballot)
        promises = self.transport.filter_promises(p1_responses)

        if len(promises) < quorum_config.q1:
            raise ProposerError(
                f"Phase1 failed: received {len(promises)} promises, "
                f"need {quorum_config.q1} (ballot={ballot})"
            )

        # Safety: if any acceptor already accepted a value, we must
        # adopt the value from the promise with the highest accepted ballot.
        safe_value = self._pick_safe_value(promises, value)

        # ---- Phase 2 ------------------------------------------------
        p2_responses = self.transport.broadcast_phase2a(ballot, safe_value)
        accepted = self.transport.filter_accepted(p2_responses)

        if len(accepted) < quorum_config.q2:
            raise ProposerError(
                f"Phase2 failed: received {len(accepted)} acceptances, "
                f"need {quorum_config.q2} (ballot={ballot})"
            )

        return safe_value

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_ballot(self) -> BallotNumber:
        self._round += 1
        return BallotNumber(round=self._round, proposer_id=self.proposer_id)

    @staticmethod
    def _pick_safe_value(promises: list[Message], proposed_value: Any) -> Any:
        """Return the value we are safe to propose in Phase 2.

        Among all promises that carry an *accepted_ballot*, we pick the one
        with the highest ballot and re-propose its *accepted_value*.  If no
        promise carries a previously accepted value we are free to use the
        caller-supplied *proposed_value*.
        """
        best_ballot: BallotNumber | None = None
        best_value: Any = proposed_value

        for promise in promises:
            if promise.type != MessageType.PHASE1B:
                continue
            acc_ballot = promise.highest_accepted_ballot
            acc_value = promise.highest_accepted_value
            if acc_ballot is not None:
                if best_ballot is None or acc_ballot > best_ballot:
                    best_ballot = acc_ballot
                    best_value = acc_value

        return best_value
