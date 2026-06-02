"""Raft protocol domain types."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class NodeState(str, enum.Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class MessageType(str, enum.Enum):
    VOTE_REQUEST = "vote_request"
    VOTE_RESPONSE = "vote_response"
    APPEND_ENTRIES = "append_entries"
    APPEND_RESPONSE = "append_response"
    CLIENT_WRITE = "client_write"
    CLIENT_READ = "client_read"


@dataclass
class LogEntry:
    term: int
    index: int
    command: str  # e.g. "SET key value" or "DEL key"
    client_id: str = ""


@dataclass
class RaftMessage:
    type: MessageType
    sender: str
    receiver: str
    term: int
    # Vote fields
    last_log_index: int = 0
    last_log_term: int = 0
    vote_granted: bool = False
    # AppendEntries fields
    leader_id: str = ""
    prev_log_index: int = 0
    prev_log_term: int = 0
    entries: list[LogEntry] = field(default_factory=list)
    leader_commit: int = 0
    success: bool = False
    match_index: int = 0
    # Client
    command: str = ""
    value: str = ""
