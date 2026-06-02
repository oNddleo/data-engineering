"""Single Raft node — leader election and log replication state machine."""

from __future__ import annotations

import random
from collections import deque

from raftmeta.schema import LogEntry, MessageType, NodeState, RaftMessage

_ELECTION_TIMEOUT_MIN = 150
_ELECTION_TIMEOUT_MAX = 300
_HEARTBEAT_INTERVAL = 50  # ticks


class RaftNode:
    """Simulated Raft node.

    Communicates via message queues rather than network sockets, making it
    deterministic and testable without any I/O.
    """

    def __init__(self, node_id: str, peers: list[str], seed: int | None = None) -> None:
        self.node_id = node_id
        self.peers = list(peers)
        self._rng = random.Random(seed)

        # Persistent state
        self.current_term = 0
        self.voted_for: str | None = None
        self.log: list[LogEntry] = []

        # Volatile state
        self.state = NodeState.FOLLOWER
        self.commit_index = -1
        self.last_applied = -1

        # Leader state
        self.next_index: dict[str, int] = {}
        self.match_index: dict[str, int] = {}

        # Election timer
        self._election_timeout = self._new_timeout()
        self._ticks_since_heartbeat = 0
        self._heartbeat_ticks = 0

        # Votes received this election
        self._votes_received: set[str] = set()

        # Applied KV state machine
        self.kv: dict[str, str] = {}

        # Outbound message queue
        self.outbox: deque[RaftMessage] = deque()

        # Leader identity
        self.leader_id: str | None = None

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _new_timeout(self) -> int:
        return self._rng.randint(_ELECTION_TIMEOUT_MIN, _ELECTION_TIMEOUT_MAX)

    @property
    def _quorum(self) -> int:
        return (len(self.peers) + 1) // 2 + 1

    @property
    def _last_log_index(self) -> int:
        return len(self.log) - 1

    @property
    def _last_log_term(self) -> int:
        return self.log[-1].term if self.log else 0

    def _send(self, msg: RaftMessage) -> None:
        self.outbox.append(msg)

    def _broadcast(self, msg_fn: object) -> None:
        for peer in self.peers:
            msg = msg_fn(peer)  # type: ignore[operator]
            self._send(msg)

    # ── Term management ────────────────────────────────────────────────────────

    def _update_term(self, term: int) -> None:
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self._become_follower()

    def _become_follower(self) -> None:
        self.state = NodeState.FOLLOWER
        self._election_timeout = self._new_timeout()
        self._ticks_since_heartbeat = 0

    def _become_candidate(self) -> None:
        self.current_term += 1
        self.state = NodeState.CANDIDATE
        self.voted_for = self.node_id
        self._votes_received = {self.node_id}
        self._election_timeout = self._new_timeout()
        self._ticks_since_heartbeat = 0
        self._request_votes()

    def _become_leader(self) -> None:
        self.state = NodeState.LEADER
        self.leader_id = self.node_id
        for peer in self.peers:
            self.next_index[peer] = len(self.log)
            self.match_index[peer] = -1
        self._send_heartbeats()

    # ── Leader election ────────────────────────────────────────────────────────

    def _request_votes(self) -> None:
        for peer in self.peers:
            self._send(
                RaftMessage(
                    type=MessageType.VOTE_REQUEST,
                    sender=self.node_id,
                    receiver=peer,
                    term=self.current_term,
                    last_log_index=self._last_log_index,
                    last_log_term=self._last_log_term,
                )
            )

    def _handle_vote_request(self, msg: RaftMessage) -> None:
        self._update_term(msg.term)
        grant = False
        if msg.term >= self.current_term:
            log_ok = msg.last_log_term > self._last_log_term or (
                msg.last_log_term == self._last_log_term
                and msg.last_log_index >= self._last_log_index
            )
            if (self.voted_for is None or self.voted_for == msg.sender) and log_ok:
                grant = True
                self.voted_for = msg.sender
                self._ticks_since_heartbeat = 0
        self._send(
            RaftMessage(
                type=MessageType.VOTE_RESPONSE,
                sender=self.node_id,
                receiver=msg.sender,
                term=self.current_term,
                vote_granted=grant,
            )
        )

    def _handle_vote_response(self, msg: RaftMessage) -> None:
        self._update_term(msg.term)
        if self.state != NodeState.CANDIDATE or msg.term != self.current_term:
            return
        if msg.vote_granted:
            self._votes_received.add(msg.sender)
            if len(self._votes_received) >= self._quorum:
                self._become_leader()

    # ── Log replication ────────────────────────────────────────────────────────

    def _send_heartbeats(self) -> None:
        for peer in self.peers:
            prev_idx = self.next_index.get(peer, len(self.log)) - 1
            prev_term = self.log[prev_idx].term if 0 <= prev_idx < len(self.log) else 0
            entries = self.log[prev_idx + 1 :]
            self._send(
                RaftMessage(
                    type=MessageType.APPEND_ENTRIES,
                    sender=self.node_id,
                    receiver=peer,
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=prev_idx,
                    prev_log_term=prev_term,
                    entries=list(entries),
                    leader_commit=self.commit_index,
                )
            )

    def _handle_append_entries(self, msg: RaftMessage) -> None:
        self._update_term(msg.term)
        self.leader_id = msg.leader_id
        success = False

        if msg.term >= self.current_term:
            self._ticks_since_heartbeat = 0
            if self.state != NodeState.FOLLOWER:
                self._become_follower()

            # Check log consistency
            if msg.prev_log_index == -1 or (
                msg.prev_log_index < len(self.log)
                and self.log[msg.prev_log_index].term == msg.prev_log_term
            ):
                success = True
                insert_idx = msg.prev_log_index + 1
                for i, entry in enumerate(msg.entries):
                    pos = insert_idx + i
                    if pos < len(self.log):
                        if self.log[pos].term != entry.term:
                            self.log = self.log[:pos]
                            self.log.append(entry)
                    else:
                        self.log.append(entry)
                if msg.leader_commit > self.commit_index:
                    self.commit_index = min(msg.leader_commit, len(self.log) - 1)
                    self._apply_committed()

        match_idx = len(self.log) - 1 if success else -1
        self._send(
            RaftMessage(
                type=MessageType.APPEND_RESPONSE,
                sender=self.node_id,
                receiver=msg.sender,
                term=self.current_term,
                success=success,
                match_index=match_idx,
            )
        )

    def _handle_append_response(self, msg: RaftMessage) -> None:
        self._update_term(msg.term)
        if self.state != NodeState.LEADER:
            return
        peer = msg.sender
        if msg.success:
            self.match_index[peer] = msg.match_index
            self.next_index[peer] = msg.match_index + 1
            self._advance_commit()
        else:
            self.next_index[peer] = max(0, self.next_index.get(peer, 1) - 1)
            self._send_heartbeats()

    def _advance_commit(self) -> None:
        for n in range(len(self.log) - 1, self.commit_index, -1):
            if self.log[n].term != self.current_term:
                continue
            replicated = 1 + sum(1 for m in self.match_index.values() if m >= n)
            if replicated >= self._quorum:
                self.commit_index = n
                self._apply_committed()
                break

    def _apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self._apply(entry)

    def _apply(self, entry: LogEntry) -> None:
        parts = entry.command.split(maxsplit=2)
        if not parts:
            return
        op = parts[0].upper()
        if op == "SET" and len(parts) == 3:
            self.kv[parts[1]] = parts[2]
        elif op == "DEL" and len(parts) == 2:
            self.kv.pop(parts[1], None)

    # ── Client commands (leader only) ─────────────────────────────────────────

    def client_write(self, command: str, client_id: str = "") -> bool:
        """Append a command to the log (leader only). Returns True if accepted."""
        if self.state != NodeState.LEADER:
            return False
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log),
            command=command,
            client_id=client_id,
        )
        self.log.append(entry)
        # Do NOT update match_index[self] — leader is already counted as 1 in _advance_commit
        self._send_heartbeats()
        return True

    def client_read(self, key: str) -> str | None:
        """Read a key (leader returns committed state)."""
        if self.state != NodeState.LEADER:
            return None
        return self.kv.get(key)

    # ── Tick ──────────────────────────────────────────────────────────────────

    def tick(self) -> None:
        """Advance simulated time by one tick."""
        self._ticks_since_heartbeat += 1
        if self.state == NodeState.LEADER:
            self._heartbeat_ticks += 1
            if self._heartbeat_ticks >= _HEARTBEAT_INTERVAL:
                self._heartbeat_ticks = 0
                self._send_heartbeats()
        elif self._ticks_since_heartbeat >= self._election_timeout:
            self._become_candidate()

    # ── Receive ───────────────────────────────────────────────────────────────

    def receive(self, msg: RaftMessage) -> None:
        """Process a single inbound message."""
        handlers = {
            MessageType.VOTE_REQUEST: self._handle_vote_request,
            MessageType.VOTE_RESPONSE: self._handle_vote_response,
            MessageType.APPEND_ENTRIES: self._handle_append_entries,
            MessageType.APPEND_RESPONSE: self._handle_append_response,
        }
        handler = handlers.get(msg.type)
        if handler:
            handler(msg)
