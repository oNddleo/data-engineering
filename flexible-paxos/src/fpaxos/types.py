from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class BallotNumber:
    """Totally-ordered ballot identifier: (round, proposer_id)."""

    round: int
    proposer_id: int

    def __lt__(self, other: BallotNumber) -> bool:
        return (self.round, self.proposer_id) < (other.round, other.proposer_id)

    def __le__(self, other: BallotNumber) -> bool:
        return self == other or self < other

    def __gt__(self, other: BallotNumber) -> bool:
        return not self <= other

    def __ge__(self, other: BallotNumber) -> bool:
        return not self < other


# Sentinel for "no ballot" comparisons
_MIN_BALLOT = BallotNumber(round=-1, proposer_id=-1)


@dataclass
class AcceptorState:
    """Durable state that each acceptor must persist."""

    promised_ballot: BallotNumber | None = None
    accepted_ballot: BallotNumber | None = None
    accepted_value: Any | None = None


class MessageType(Enum):
    PHASE1A = "phase1a"  # Prepare
    PHASE1B = "phase1b"  # Promise
    PHASE2A = "phase2a"  # Accept
    PHASE2B = "phase2b"  # Accepted
    NACK = "nack"  # Rejected


@dataclass
class Message:
    """Wire-format message exchanged between proposers and acceptors."""

    type: MessageType
    ballot: BallotNumber
    value: Any | None = None
    highest_accepted_ballot: BallotNumber | None = None
    highest_accepted_value: Any | None = None
    sender_id: int = 0  # acceptor node id


@dataclass
class QuorumConfig:
    """Encodes a flexible quorum pair: Q1 + Q2 > n must hold."""

    n: int  # total number of acceptors
    q1: int  # Phase-1 (leader election) quorum size
    q2: int  # Phase-2 (value proposal) quorum size

    def __post_init__(self) -> None:
        if self.q1 + self.q2 <= self.n:
            raise ValueError(
                f"Quorum constraint violated: Q1({self.q1}) + Q2({self.q2}) must be > n({self.n})"
            )
        if self.q1 < 1 or self.q2 < 1:
            raise ValueError("Q1 and Q2 must each be at least 1")
        if self.q1 > self.n or self.q2 > self.n:
            raise ValueError("Q1 and Q2 cannot exceed n")


@dataclass
class OperationRecord:
    """A single operation entry used by the linearizability checker."""

    start_time: float
    end_time: float
    op_type: str  # "read" or "write"
    value: Any | None
    # For reads: the value observed; for writes: the value written.
    read_value: Any | None = field(default=None)
