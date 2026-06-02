"""Data types for BFT stream processing."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class MessageType(str, enum.Enum):
    PRE_PREPARE = "PRE_PREPARE"
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    VIEW_CHANGE = "VIEW_CHANGE"
    NEW_VIEW = "NEW_VIEW"


class ReplicaState(str, enum.Enum):
    NORMAL = "NORMAL"
    VIEW_CHANGE = "VIEW_CHANGE"
    FAULTY = "FAULTY"


@dataclass(frozen=True)
class StreamRecord:
    """A single event in the stream."""

    timestamp: float  # logical clock tick
    key: str
    value: float
    window_id: int  # which window this record belongs to


@dataclass
class WindowAggregate:
    """Accumulated state for one tumbling window."""

    window_id: int
    record_count: int = field(default=0)
    value_sum: float = field(default=0.0)
    checksum: int = field(default=0)  # Σ hash(record)
    committed: bool = field(default=False)

    def ingest(self, record: StreamRecord) -> None:
        self.record_count += 1
        self.value_sum += record.value
        self.checksum ^= hash((record.key, record.value, record.timestamp))


@dataclass(frozen=True)
class WatermarkProposal:
    """Primary proposes that window ``window_id`` is ready to close."""

    view: int
    seq: int  # proposal sequence number
    window_id: int
    record_count: int
    checksum: int
    proposer_id: str


@dataclass(frozen=True)
class BFTMessage:
    """Envelope for all PBFT messages."""

    type: MessageType
    sender: str
    receiver: str
    view: int
    seq: int
    proposal: WatermarkProposal | None = field(default=None)
    # digest used in PREPARE / COMMIT phases
    digest: int = field(default=0)
