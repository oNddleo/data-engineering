"""Comprehensive tests for the flexible-paxos Python package.

Coverage
--------
- BallotNumber: ordering, equality
- Acceptor: promise tracking, accept, reject, NACK
- Proposer: 3-node cluster, flexible quorums, competing proposers, safety
- QuorumConfig: constraint validation
- QuorumManager: dynamic adjustment, constraint always holds
- LinearizabilityChecker: empty, consistent, violation
- Hypothesis-style property tests (pure Python, no hypothesis dependency)
"""

from __future__ import annotations

import itertools

import pytest

from fpaxos.acceptor import Acceptor
from fpaxos.linearizability import HistoryEntry, LinearizabilityChecker
from fpaxos.proposer import Proposer, ProposerError
from fpaxos.quorum import QuorumManager
from fpaxos.transport import InMemoryTransport
from fpaxos.types import BallotNumber, MessageType, QuorumConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_cluster(n: int) -> tuple[InMemoryTransport, list[Acceptor]]:
    transport = InMemoryTransport()
    acceptors = [Acceptor(node_id=i) for i in range(n)]
    for a in acceptors:
        transport.register(a)
    return transport, acceptors


def majority(n: int) -> int:
    return n // 2 + 1


def classic_config(n: int) -> QuorumConfig:
    m = majority(n)
    return QuorumConfig(n=n, q1=m, q2=m)


# ===========================================================================
# 1. BallotNumber
# ===========================================================================


class TestBallotNumber:
    def test_equality(self) -> None:
        assert BallotNumber(1, 0) == BallotNumber(1, 0)

    def test_inequality_round(self) -> None:
        assert BallotNumber(1, 0) != BallotNumber(2, 0)

    def test_lt_by_round(self) -> None:
        assert BallotNumber(1, 0) < BallotNumber(2, 0)

    def test_lt_by_proposer_id(self) -> None:
        assert BallotNumber(1, 0) < BallotNumber(1, 1)

    def test_gt(self) -> None:
        assert BallotNumber(3, 5) > BallotNumber(2, 99)

    def test_le_equal(self) -> None:
        b = BallotNumber(2, 2)
        assert b <= b

    def test_le_less(self) -> None:
        assert BallotNumber(1, 0) <= BallotNumber(1, 1)

    def test_ge_equal(self) -> None:
        b = BallotNumber(5, 0)
        assert b >= b

    def test_ge_greater(self) -> None:
        assert BallotNumber(10, 0) >= BallotNumber(9, 99)

    def test_transitivity(self) -> None:
        """If a < b and b < c then a < c."""
        triples = [
            (BallotNumber(1, 0), BallotNumber(2, 0), BallotNumber(3, 0)),
            (BallotNumber(1, 0), BallotNumber(1, 1), BallotNumber(2, 0)),
            (BallotNumber(0, 0), BallotNumber(0, 1), BallotNumber(0, 2)),
        ]
        for a, b, c in triples:
            assert a < b and b < c and a < c

    def test_frozen_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        b = BallotNumber(1, 0)
        with pytest.raises(FrozenInstanceError):
            b.round = 99  # type: ignore[misc]

    def test_ordering_is_total(self) -> None:
        """Every pair is comparable: exactly one of <, ==, > holds."""
        ballots = [BallotNumber(r, p) for r in range(3) for p in range(3)]
        for a, b in itertools.combinations(ballots, 2):
            assert (a < b) ^ (a == b) ^ (a > b)


# ===========================================================================
# 2. QuorumConfig
# ===========================================================================


class TestQuorumConfig:
    def test_valid_majority(self) -> None:
        cfg = QuorumConfig(n=5, q1=3, q2=3)
        assert cfg.q1 == 3 and cfg.q2 == 3

    def test_valid_write_optimized(self) -> None:
        cfg = QuorumConfig(n=5, q1=4, q2=2)
        assert cfg.q1 + cfg.q2 > cfg.n

    def test_valid_read_optimized(self) -> None:
        cfg = QuorumConfig(n=5, q1=2, q2=4)
        assert cfg.q1 + cfg.q2 > cfg.n

    def test_violation_raises(self) -> None:
        with pytest.raises(ValueError, match="Quorum constraint violated"):
            QuorumConfig(n=5, q1=2, q2=3)  # 2+3=5, not > 5

    def test_zero_q1_raises(self) -> None:
        with pytest.raises(ValueError):
            QuorumConfig(n=5, q1=0, q2=6)

    def test_q_exceeds_n_raises(self) -> None:
        with pytest.raises(ValueError):
            QuorumConfig(n=5, q1=6, q2=1)


# ===========================================================================
# 3. Acceptor
# ===========================================================================


class TestAcceptor:
    def test_initial_state_is_empty(self) -> None:
        a = Acceptor(0)
        assert a.promised_ballot is None
        assert a.accepted_ballot is None
        assert a.accepted_value is None

    def test_promise_first_ballot(self) -> None:
        a = Acceptor(0)
        b = BallotNumber(1, 0)
        msg = a.handle_phase1a(b)
        assert msg.type == MessageType.PHASE1B
        assert msg.ballot == b
        assert a.promised_ballot == b

    def test_promise_higher_ballot(self) -> None:
        a = Acceptor(0)
        a.handle_phase1a(BallotNumber(1, 0))
        msg = a.handle_phase1a(BallotNumber(2, 0))
        assert msg.type == MessageType.PHASE1B
        assert a.promised_ballot == BallotNumber(2, 0)

    def test_nack_lower_ballot(self) -> None:
        a = Acceptor(0)
        a.handle_phase1a(BallotNumber(5, 0))
        msg = a.handle_phase1a(BallotNumber(3, 0))
        assert msg.type == MessageType.NACK

    def test_nack_equal_ballot_phase1(self) -> None:
        a = Acceptor(0)
        b = BallotNumber(1, 0)
        a.handle_phase1a(b)
        # Equal ballot should NACK (not strictly greater)
        msg = a.handle_phase1a(b)
        assert msg.type == MessageType.NACK

    def test_accept_matching_ballot(self) -> None:
        a = Acceptor(0)
        b = BallotNumber(1, 0)
        a.handle_phase1a(b)
        msg = a.handle_phase2a(b, "v1")
        assert msg.type == MessageType.PHASE2B
        assert msg.value == "v1"
        assert a.accepted_value == "v1"

    def test_accept_higher_ballot_phase2(self) -> None:
        a = Acceptor(0)
        a.handle_phase1a(BallotNumber(1, 0))
        msg = a.handle_phase2a(BallotNumber(2, 0), "v2")
        assert msg.type == MessageType.PHASE2B

    def test_nack_lower_ballot_phase2(self) -> None:
        a = Acceptor(0)
        a.handle_phase1a(BallotNumber(5, 0))
        msg = a.handle_phase2a(BallotNumber(3, 0), "v_old")
        assert msg.type == MessageType.NACK
        assert a.accepted_value is None

    def test_promise_includes_accepted_value(self) -> None:
        a = Acceptor(0)
        b1 = BallotNumber(1, 0)
        a.handle_phase1a(b1)
        a.handle_phase2a(b1, "existing_value")
        b2 = BallotNumber(2, 0)
        msg = a.handle_phase1a(b2)
        assert msg.type == MessageType.PHASE1B
        assert msg.highest_accepted_ballot == b1
        assert msg.highest_accepted_value == "existing_value"

    def test_sender_id_in_response(self) -> None:
        a = Acceptor(node_id=42)
        msg = a.handle_phase1a(BallotNumber(1, 0))
        assert msg.sender_id == 42


# ===========================================================================
# 4. InMemoryTransport
# ===========================================================================


class TestTransport:
    def test_register_and_count(self) -> None:
        transport, acceptors = make_cluster(5)
        assert transport.acceptor_count() == 5

    def test_broadcast_phase1a_returns_all_promises(self) -> None:
        transport, _ = make_cluster(3)
        responses = transport.broadcast_phase1a(BallotNumber(1, 0))
        assert len(responses) == 3
        promises = transport.filter_promises(responses)
        assert len(promises) == 3

    def test_drop_node_reduces_responses(self) -> None:
        transport, _ = make_cluster(5)
        transport.drop_node(0)
        transport.drop_node(1)
        responses = transport.broadcast_phase1a(BallotNumber(1, 0))
        assert len(responses) == 3

    def test_restore_node_resumes_responses(self) -> None:
        transport, _ = make_cluster(3)
        transport.drop_node(0)
        transport.restore_node(0)
        responses = transport.broadcast_phase1a(BallotNumber(1, 0))
        assert len(responses) == 3

    def test_message_log_accumulates(self) -> None:
        transport, _ = make_cluster(3)
        transport.broadcast_phase1a(BallotNumber(1, 0))
        assert len(transport.message_log) == 3


# ===========================================================================
# 5. Proposer – 3-node cluster, classic majority
# ===========================================================================


class TestProposerClassic:
    def test_single_proposer_commits(self) -> None:
        transport, _ = make_cluster(3)
        proposer = Proposer(proposer_id=0, transport=transport)
        decided = proposer.propose("foo", classic_config(3))
        assert decided == "foo"

    def test_single_proposer_5_nodes(self) -> None:
        transport, _ = make_cluster(5)
        proposer = Proposer(proposer_id=0, transport=transport)
        decided = proposer.propose(42, classic_config(5))
        assert decided == 42

    def test_proposer_increments_ballot(self) -> None:
        transport, _ = make_cluster(3)
        proposer = Proposer(proposer_id=0, transport=transport)
        proposer.propose("a", classic_config(3))
        proposer.propose("b", classic_config(3))
        # Both rounds should succeed (rounds 1 and 2)
        assert proposer._round == 2  # noqa: SLF001

    def test_proposal_fails_when_quorum_unavailable(self) -> None:
        transport, _ = make_cluster(3)
        transport.drop_node(0)
        transport.drop_node(1)
        # Only 1 node alive, need majority=2
        proposer = Proposer(proposer_id=0, transport=transport)
        with pytest.raises(ProposerError):
            proposer.propose("x", classic_config(3))


# ===========================================================================
# 6. Flexible Quorums
# ===========================================================================


class TestFlexibleQuorums:
    def test_write_optimized_q1_4_q2_2_n5(self) -> None:
        """Q1=4, Q2=2 on 5 nodes: write-optimised, 4+2=6>5."""
        transport, _ = make_cluster(5)
        proposer = Proposer(proposer_id=0, transport=transport)
        cfg = QuorumConfig(n=5, q1=4, q2=2)
        decided = proposer.propose("write_opt", cfg)
        assert decided == "write_opt"

    def test_read_optimized_q1_2_q2_4_n5(self) -> None:
        """Q1=2, Q2=4 on 5 nodes: read-optimised, 2+4=6>5."""
        transport, _ = make_cluster(5)
        proposer = Proposer(proposer_id=0, transport=transport)
        cfg = QuorumConfig(n=5, q1=2, q2=4)
        decided = proposer.propose("read_opt", cfg)
        assert decided == "read_opt"

    def test_write_optimized_insufficient_q1_fails(self) -> None:
        """Drop 2 nodes so only 3 alive; Q1=4 can't be satisfied."""
        transport, _ = make_cluster(5)
        transport.drop_node(0)
        transport.drop_node(1)
        proposer = Proposer(proposer_id=0, transport=transport)
        cfg = QuorumConfig(n=5, q1=4, q2=2)
        with pytest.raises(ProposerError, match="Phase1"):
            proposer.propose("x", cfg)

    def test_read_optimized_insufficient_q2_fails(self) -> None:
        """Drop 2 nodes so only 3 alive; Q2=4 can't be satisfied."""
        transport, _ = make_cluster(5)
        transport.drop_node(0)
        transport.drop_node(1)
        proposer = Proposer(proposer_id=0, transport=transport)
        cfg = QuorumConfig(n=5, q1=2, q2=4)
        # Phase1 (q1=2) passes with 3 live nodes, but Phase2 (q2=4) fails
        with pytest.raises(ProposerError, match="Phase2"):
            proposer.propose("x", cfg)

    def test_min_quorum_n1(self) -> None:
        """Single-node cluster: Q1=1, Q2=1."""
        transport, _ = make_cluster(1)
        proposer = Proposer(proposer_id=0, transport=transport)
        cfg = QuorumConfig(n=1, q1=1, q2=1)
        decided = proposer.propose("solo", cfg)
        assert decided == "solo"


# ===========================================================================
# 7. Competing Proposers
# ===========================================================================


class TestCompetingProposers:
    def test_higher_ballot_adopts_accepted_value(self) -> None:
        """A second proposer with a higher ballot MUST adopt the already-accepted value.

        This is the core Paxos safety guarantee: once a value is chosen by a quorum
        in Phase 2, every subsequent proposer that sees those acceptors in Phase 1
        learns of the accepted value and is *required* to re-propose it, not its
        own value.  This ensures only one value is ever decided.
        """
        transport, _ = make_cluster(3)
        p1 = Proposer(proposer_id=0, transport=transport)
        p2 = Proposer(proposer_id=1, transport=transport)

        # p1 completes a full round; value_from_p1 is now accepted by a quorum.
        p1.propose("value_from_p1", classic_config(3))  # round 1

        # p2 uses a higher ballot — advances past p1's round.
        p2._round = 1  # noqa: SLF001
        decided = p2.propose("value_from_p2", classic_config(3))
        # Paxos safety: p2's Phase-1 replies carry "value_from_p1" as the
        # highest-ballot accepted value, so p2 MUST propose that, not "value_from_p2".
        assert decided == "value_from_p1"

    def test_lower_ballot_nacked(self) -> None:
        """A proposer whose ballot is too low gets NACKed in Phase1."""
        transport, _ = make_cluster(3)

        # Manually promise a high ballot on all acceptors
        high_ballot = BallotNumber(round=100, proposer_id=0)
        transport.broadcast_phase1a(high_ballot)

        # Now try a low ballot
        low_ballot = BallotNumber(round=1, proposer_id=99)
        responses = transport.broadcast_phase1a(low_ballot)
        nacks = transport.filter_nacks(responses)
        assert len(nacks) == 3  # all acceptors NACK the low ballot

    def test_two_proposers_higher_ballot_adopts_committed_value(self) -> None:
        """Safety: proposer with higher ballot inherits the already-committed value.

        Even when p_high's ballot (1,1) strictly beats p_low's (1,0), Paxos
        safety requires p_high to re-propose the value p_low already got accepted
        by a quorum.  The tie-break ordering only matters for *winning* Phase 1;
        it does not override a value that was already accepted.
        """
        transport, _ = make_cluster(3)
        p_low = Proposer(proposer_id=0, transport=transport)
        p_high = Proposer(proposer_id=1, transport=transport)

        # Both use round=1; id=1 > id=0
        p_low._round = 0  # noqa: SLF001  — next ballot will be (1,0)
        p_high._round = 0  # noqa: SLF001 — next ballot will be (1,1)

        # p_low goes first and successfully accepts "low_value" at a quorum.
        p_low.propose("low_value", classic_config(3))
        # p_high's Phase-1 sees "low_value" accepted → must re-propose it.
        decided = p_high.propose("high_value", classic_config(3))
        assert decided == "low_value"


# ===========================================================================
# 8. Safety – previously accepted value must be re-proposed
# ===========================================================================


class TestSafety:
    def test_previously_accepted_value_is_adopted(self) -> None:
        """Phase1 reveals an already-accepted value; proposer must re-use it."""
        transport, acceptors = make_cluster(3)

        # Round 1: proposer 0 completes phase1 and phase2 on acceptors 0,1.
        b1 = BallotNumber(round=1, proposer_id=0)
        # Manually accept "original" on acceptors 0 and 1
        acceptors[0].handle_phase1a(b1)
        acceptors[1].handle_phase1a(b1)
        acceptors[0].handle_phase2a(b1, "original")
        acceptors[1].handle_phase2a(b1, "original")
        # Acceptor 2 has not seen anything yet.

        # Round 2: proposer 1 runs phase1 on all 3 acceptors.
        # It will learn about "original" from acceptors 0 and 1.
        p2 = Proposer(proposer_id=1, transport=transport)
        decided = p2.propose("new_value", classic_config(3))

        # Safety: "original" must be decided, not "new_value".
        assert decided == "original"

    def test_highest_ballot_accepted_value_used(self) -> None:
        """Among multiple accepted values, the highest-ballot one wins."""
        transport, acceptors = make_cluster(5)

        b1 = BallotNumber(round=1, proposer_id=0)
        b2 = BallotNumber(round=2, proposer_id=0)

        # Acceptor 0: accepted "value_b1" in round 1
        acceptors[0].handle_phase1a(b1)
        acceptors[0].handle_phase2a(b1, "value_b1")

        # Acceptor 1: accepted "value_b2" in round 2 (higher ballot)
        acceptors[1].handle_phase1a(b2)
        acceptors[1].handle_phase2a(b2, "value_b2")

        # Proposer with a higher ballot learns from all five acceptors.
        proposer = Proposer(proposer_id=99, transport=transport)
        proposer._round = 2  # noqa: SLF001  — next ballot = (3, 99)
        decided = proposer.propose("ignored", classic_config(5))

        # Must pick value_b2 (from the higher ballot b2).
        assert decided == "value_b2"


# ===========================================================================
# 9. QuorumManager
# ===========================================================================


class TestQuorumManager:
    def test_balanced_gives_majority(self) -> None:
        mgr = QuorumManager(5)
        for _ in range(50):
            mgr.record_write()
            mgr.record_read()
        cfg = mgr.get_config()
        assert cfg.q1 == 3 and cfg.q2 == 3

    def test_write_heavy_gives_small_q2(self) -> None:
        mgr = QuorumManager(5)
        for _ in range(80):
            mgr.record_write()
        for _ in range(20):
            mgr.record_read()
        cfg = mgr.get_config()
        # write_ratio=0.8 → write-optimized
        assert cfg.q2 < cfg.q1

    def test_read_heavy_gives_small_q1(self) -> None:
        mgr = QuorumManager(5)
        for _ in range(20):
            mgr.record_write()
        for _ in range(80):
            mgr.record_read()
        cfg = mgr.get_config()
        # read_ratio=0.8 → read-optimized
        assert cfg.q1 < cfg.q2

    def test_constraint_always_held_write_heavy(self) -> None:
        for n in range(1, 20):
            mgr = QuorumManager(n)
            for _ in range(100):
                mgr.record_write()
            cfg = mgr.get_config()
            assert cfg.q1 + cfg.q2 > n, f"Failed for n={n}: q1={cfg.q1}, q2={cfg.q2}"

    def test_constraint_always_held_read_heavy(self) -> None:
        for n in range(1, 20):
            mgr = QuorumManager(n)
            for _ in range(100):
                mgr.record_read()
            cfg = mgr.get_config()
            assert cfg.q1 + cfg.q2 > n, f"Failed for n={n}: q1={cfg.q1}, q2={cfg.q2}"

    def test_constraint_always_held_balanced(self) -> None:
        for n in range(1, 20):
            mgr = QuorumManager(n)
            for _ in range(50):
                mgr.record_write()
                mgr.record_read()
            cfg = mgr.get_config()
            assert cfg.q1 + cfg.q2 > n, f"Failed for n={n}: q1={cfg.q1}, q2={cfg.q2}"

    def test_manual_override_valid(self) -> None:
        mgr = QuorumManager(5)
        cfg = mgr.set_config(q1=4, q2=2)
        assert cfg.q1 == 4 and cfg.q2 == 2

    def test_manual_override_invalid_raises(self) -> None:
        mgr = QuorumManager(5)
        with pytest.raises(ValueError):
            mgr.set_config(q1=2, q2=3)  # 2+3=5, not >5

    def test_no_operations_defaults_to_balanced(self) -> None:
        mgr = QuorumManager(5)
        assert mgr.write_ratio == 0.5
        cfg = mgr.get_config()
        assert cfg.q1 == cfg.q2

    def test_counters(self) -> None:
        mgr = QuorumManager(3)
        mgr.record_write()
        mgr.record_write()
        mgr.record_read()
        assert mgr.write_count == 2
        assert mgr.read_count == 1
        assert mgr.total_operations == 3

    def test_n1_always_valid(self) -> None:
        mgr = QuorumManager(1)
        for _ in range(10):
            mgr.record_write()
        cfg = mgr.get_config()
        assert cfg.q1 >= 1 and cfg.q2 >= 1 and cfg.q1 + cfg.q2 > 1


# ===========================================================================
# 10. LinearizabilityChecker
# ===========================================================================


class TestLinearizabilityChecker:
    def test_empty_history_is_linearizable(self) -> None:
        checker = LinearizabilityChecker()
        assert checker.check_history([]) is True

    def test_single_write_linearizable(self) -> None:
        checker = LinearizabilityChecker()
        history = [HistoryEntry(0.0, 1.0, "write", "a")]
        assert checker.check_history(history) is True

    def test_single_read_after_write_linearizable(self) -> None:
        checker = LinearizabilityChecker()
        history = [
            HistoryEntry(0.0, 1.0, "write", "a"),
            HistoryEntry(1.5, 2.5, "read", "a"),
        ]
        assert checker.check_history(history) is True

    def test_consistent_sequential_history(self) -> None:
        """write("x") then read("x") then write("y") then read("y")."""
        checker = LinearizabilityChecker()
        history = [
            HistoryEntry(0.0, 1.0, "write", "x"),
            HistoryEntry(1.1, 2.0, "read", "x"),
            HistoryEntry(2.1, 3.0, "write", "y"),
            HistoryEntry(3.1, 4.0, "read", "y"),
        ]
        assert checker.check_history(history) is True

    def test_violation_read_stale_after_overwrite(self) -> None:
        """Read 'old' after 'new' was fully written and committed."""
        checker = LinearizabilityChecker()
        history = [
            HistoryEntry(0.0, 1.0, "write", "old"),
            HistoryEntry(1.1, 2.0, "write", "new"),
            # Read happens AFTER 'new' is fully committed but sees 'old' → violation
            HistoryEntry(2.5, 3.5, "read", "old"),
        ]
        assert checker.check_history(history) is False

    def test_read_nonexistent_value_is_violation(self) -> None:
        """Read returns a value that was never written."""
        checker = LinearizabilityChecker()
        history = [
            HistoryEntry(0.0, 1.0, "write", "a"),
            HistoryEntry(1.5, 2.5, "read", "ghost"),  # never written
        ]
        assert checker.check_history(history) is False

    def test_internal_record_and_check(self) -> None:
        checker = LinearizabilityChecker()
        checker.record(0.0, 1.0, "write", "v1")
        checker.record(1.5, 2.5, "read", "v1")
        assert checker.check_history() is True

    def test_clear_resets_history(self) -> None:
        checker = LinearizabilityChecker()
        checker.record(0.0, 1.0, "write", "x")
        checker.clear()
        assert checker.history == []
        assert checker.check_history() is True

    def test_only_writes_linearizable(self) -> None:
        checker = LinearizabilityChecker()
        history = [
            HistoryEntry(0.0, 1.0, "write", "a"),
            HistoryEntry(1.1, 2.0, "write", "b"),
            HistoryEntry(2.1, 3.0, "write", "c"),
        ]
        assert checker.check_history(history) is True


# ===========================================================================
# 11. Property-based style tests (pure Python, no Hypothesis)
# ===========================================================================


class TestProperties:
    def test_ballot_ordering_transitive_exhaustive(self) -> None:
        """Exhaustive transitivity over a small domain."""
        ballots = [BallotNumber(r, p) for r in range(4) for p in range(3)]
        for a in ballots:
            for b in ballots:
                for c in ballots:
                    if a < b and b < c:
                        assert a < c

    def test_quorum_constraint_many_n(self) -> None:
        """For all n from 1..30, majority quorums satisfy Q1+Q2>n."""
        for n in range(1, 31):
            cfg = classic_config(n)
            assert cfg.q1 + cfg.q2 > n

    def test_quorum_manager_constraint_all_ratios(self) -> None:
        """QuorumManager never violates Q1+Q2>n across all ratios and sizes."""
        for n in range(1, 15):
            mgr = QuorumManager(n)
            # write-only
            for _ in range(100):
                mgr.record_write()
            assert mgr.get_config().q1 + mgr.get_config().q2 > n
            mgr2 = QuorumManager(n)
            # read-only
            for _ in range(100):
                mgr2.record_read()
            assert mgr2.get_config().q1 + mgr2.get_config().q2 > n

    def test_any_valid_flexible_config_achieves_consensus(self) -> None:
        """For all valid (Q1, Q2) pairs on 5 nodes, consensus succeeds."""
        n = 5
        for q1 in range(1, n + 1):
            for q2 in range(1, n + 1):
                if q1 + q2 <= n:
                    continue  # invalid
                transport, _ = make_cluster(n)
                proposer = Proposer(proposer_id=0, transport=transport)
                cfg = QuorumConfig(n=n, q1=q1, q2=q2)
                decided = proposer.propose("test", cfg)
                assert decided == "test"
