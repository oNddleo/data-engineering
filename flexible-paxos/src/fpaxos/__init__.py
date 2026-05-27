"""Flexible Paxos consensus with dynamic quorum reconfiguration."""

from __future__ import annotations

from fpaxos.acceptor import Acceptor
from fpaxos.linearizability import HistoryEntry, LinearizabilityChecker
from fpaxos.proposer import Proposer, ProposerError
from fpaxos.quorum import QuorumManager
from fpaxos.transport import InMemoryTransport
from fpaxos.types import (
    AcceptorState,
    BallotNumber,
    Message,
    MessageType,
    OperationRecord,
    QuorumConfig,
)

__all__ = [
    "Acceptor",
    "AcceptorState",
    "BallotNumber",
    "HistoryEntry",
    "InMemoryTransport",
    "LinearizabilityChecker",
    "Message",
    "MessageType",
    "OperationRecord",
    "Proposer",
    "ProposerError",
    "QuorumConfig",
    "QuorumManager",
]

__version__ = "0.1.0"
