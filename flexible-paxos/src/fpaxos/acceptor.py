from __future__ import annotations

from typing import Any

from fpaxos.types import AcceptorState, BallotNumber, Message, MessageType


class Acceptor:
    """Single Paxos acceptor node.

    Handles Phase1a (Prepare) and Phase2a (Accept) messages, responding with
    Phase1b (Promise), Phase2b (Accepted), or NACK as appropriate.
    """

    def __init__(self, node_id: int) -> None:
        self.node_id = node_id
        self.state: AcceptorState = AcceptorState()

    # ------------------------------------------------------------------
    # Phase 1: Prepare / Promise
    # ------------------------------------------------------------------

    def handle_phase1a(self, ballot: BallotNumber) -> Message:
        """Process a Phase1a (Prepare) message.

        If *ballot* is strictly greater than any previously promised ballot,
        promise not to accept anything below *ballot* and return a PHASE1B
        carrying the highest previously accepted value (if any).

        Otherwise return a NACK so the proposer knows to retry with a higher
        ballot.
        """
        promised = self.state.promised_ballot
        if promised is None or ballot > promised:
            self.state.promised_ballot = ballot
            return Message(
                type=MessageType.PHASE1B,
                ballot=ballot,
                sender_id=self.node_id,
                highest_accepted_ballot=self.state.accepted_ballot,
                highest_accepted_value=self.state.accepted_value,
            )
        return Message(
            type=MessageType.NACK,
            ballot=ballot,
            sender_id=self.node_id,
        )

    # ------------------------------------------------------------------
    # Phase 2: Accept / Accepted
    # ------------------------------------------------------------------

    def handle_phase2a(self, ballot: BallotNumber, value: Any) -> Message:
        """Process a Phase2a (Accept) message.

        Accept if *ballot* is greater than or equal to the promised ballot
        (the proposer that completed Phase1 successfully is entitled to issue
        Phase2a with the same ballot it promised in).  Update accepted state
        and return PHASE2B.

        Otherwise NACK.
        """
        promised = self.state.promised_ballot
        if promised is None or ballot >= promised:
            self.state.promised_ballot = ballot  # refresh promise
            self.state.accepted_ballot = ballot
            self.state.accepted_value = value
            return Message(
                type=MessageType.PHASE2B,
                ballot=ballot,
                value=value,
                sender_id=self.node_id,
            )
        return Message(
            type=MessageType.NACK,
            ballot=ballot,
            sender_id=self.node_id,
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def promised_ballot(self) -> BallotNumber | None:
        return self.state.promised_ballot

    @property
    def accepted_ballot(self) -> BallotNumber | None:
        return self.state.accepted_ballot

    @property
    def accepted_value(self) -> Any:
        return self.state.accepted_value
