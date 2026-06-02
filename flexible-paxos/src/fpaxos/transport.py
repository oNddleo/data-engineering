from __future__ import annotations

from typing import TYPE_CHECKING

from fpaxos.types import BallotNumber, Message, MessageType

if TYPE_CHECKING:
    from fpaxos.acceptor import Acceptor


class InMemoryTransport:
    """Synchronous, in-process message delivery for testing.

    Maintains a registry of acceptor nodes and routes messages directly by
    calling the appropriate handler methods.  No threads, no queues — purely
    synchronous so tests are deterministic.
    """

    def __init__(self) -> None:
        self._acceptors: dict[int, Acceptor] = {}
        # Optionally simulate dropped messages for fault-injection tests
        self._dropped_nodes: set[int] = set()
        self._message_log: list[Message] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, acceptor: Acceptor) -> None:
        """Register an acceptor under its node_id."""
        self._acceptors[acceptor.node_id] = acceptor

    def drop_node(self, node_id: int) -> None:
        """Simulate a node failure: all messages to/from it are dropped."""
        self._dropped_nodes.add(node_id)

    def restore_node(self, node_id: int) -> None:
        """Bring a previously dropped node back online."""
        self._dropped_nodes.discard(node_id)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def broadcast_phase1a(self, ballot: BallotNumber) -> list[Message]:
        """Send Phase1a to all live acceptors; return their responses."""
        responses: list[Message] = []
        for node_id, acceptor in self._acceptors.items():
            if node_id in self._dropped_nodes:
                continue
            msg = acceptor.handle_phase1a(ballot)
            self._message_log.append(msg)
            responses.append(msg)
        return responses

    def broadcast_phase2a(self, ballot: BallotNumber, value: object) -> list[Message]:
        """Send Phase2a to all live acceptors; return their responses."""
        responses: list[Message] = []
        for node_id, acceptor in self._acceptors.items():
            if node_id in self._dropped_nodes:
                continue
            msg = acceptor.handle_phase2a(ballot, value)
            self._message_log.append(msg)
            responses.append(msg)
        return responses

    # ------------------------------------------------------------------
    # Filtering helpers
    # ------------------------------------------------------------------

    @staticmethod
    def filter_promises(responses: list[Message]) -> list[Message]:
        return [m for m in responses if m.type == MessageType.PHASE1B]

    @staticmethod
    def filter_accepted(responses: list[Message]) -> list[Message]:
        return [m for m in responses if m.type == MessageType.PHASE2B]

    @staticmethod
    def filter_nacks(responses: list[Message]) -> list[Message]:
        return [m for m in responses if m.type == MessageType.NACK]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def message_log(self) -> list[Message]:
        return list(self._message_log)

    def acceptor_count(self) -> int:
        return len(self._acceptors)
