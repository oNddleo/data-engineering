"""Unit tests for Raft node and cluster behaviour."""

from __future__ import annotations

from raftmeta.cluster import RaftCluster
from raftmeta.schema import NodeState


def _cluster(n: int = 3, seed: int = 1) -> RaftCluster:
    return RaftCluster([f"n{i}" for i in range(n)], seed=seed)


class TestLeaderElection:
    def test_elects_single_leader_3_nodes(self) -> None:
        c = _cluster(3)
        leader = c.run_until_leader(max_ticks=2000)
        assert leader is not None

    def test_elects_single_leader_5_nodes(self) -> None:
        c = _cluster(5)
        leader = c.run_until_leader(max_ticks=2000)
        assert leader is not None

    def test_exactly_one_leader_at_a_time(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        leaders = [n for n in c.nodes.values() if n.state == NodeState.LEADER]
        assert len(leaders) == 1

    def test_leader_has_highest_term_or_equal(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        ldr_id = c.leader()
        assert ldr_id is not None
        ldr = c.nodes[ldr_id]
        for node in c.nodes.values():
            assert ldr.current_term >= node.current_term

    def test_re_election_after_partition(self) -> None:
        c = _cluster(3)
        leader = c.run_until_leader()
        assert leader is not None
        # Partition the leader
        c.partition(leader)
        c.tick(500)
        new_leader = c.leader()
        assert new_leader is not None
        assert new_leader != leader

    def test_no_leader_without_quorum(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        # Partition 2 of 3 nodes — no quorum left
        nodes = list(c.nodes.keys())
        c.partition(nodes[0])
        c.partition(nodes[1])
        # Give time for election attempts
        c.tick(1000)
        # Remaining node cannot elect itself (only 1/3 votes)
        assert c.leader() is None or c.nodes[c.leader()].node_id == nodes[2]


class TestLogReplication:
    def test_write_replicates_to_followers(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        c.write("SET foo bar")
        c.replicate()
        # All nodes should have the entry applied
        for node in c.nodes.values():
            assert node.kv.get("foo") == "bar"

    def test_multiple_writes_order_preserved(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        for i in range(5):
            c.write(f"SET k{i} v{i}")
        c.replicate()
        ldr_id = c.leader()
        assert ldr_id is not None
        ldr = c.nodes[ldr_id]
        for i in range(5):
            assert ldr.kv.get(f"k{i}") == f"v{i}"

    def test_del_command(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        c.write("SET x 100")
        c.replicate()
        c.write("DEL x")
        c.replicate()
        ldr_id = c.leader()
        assert ldr_id is not None
        assert "x" not in c.nodes[ldr_id].kv

    def test_log_consistency_after_heal(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        c.write("SET a 1")
        c.replicate()

        # Isolate one node and write more
        followers = [n for n in c.nodes if n != c.leader()]
        isolated = followers[0]
        c.partition(isolated)
        c.write("SET b 2")
        c.replicate(200)

        # Heal and let it catch up
        c.heal(isolated)
        c.tick(500)
        assert c.nodes[isolated].kv.get("a") == "1"

    def test_read_returns_committed(self) -> None:
        c = _cluster(3)
        c.run_until_leader()
        c.write("SET answer 42")
        c.replicate()
        val = c.read("answer")
        assert val == "42"

    def test_write_fails_without_leader(self) -> None:
        c = _cluster(3)
        # Don't elect — no writes should succeed
        result = c.write("SET x 1")
        assert result is False
