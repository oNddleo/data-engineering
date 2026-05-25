"""Hypothesis property tests for Raft safety properties."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from raftmeta.cluster import RaftCluster
from raftmeta.schema import NodeState


def _cluster(n: int, seed: int) -> RaftCluster:
    return RaftCluster([f"n{i}" for i in range(n)], seed=seed)


class TestRaftSafetyProperties:
    @given(
        st.integers(
            min_value=3,
            max_value=5,
        ).filter(lambda n: n % 2 == 1),
        st.integers(min_value=0, max_value=99),
    )
    @settings(max_examples=20)
    def test_at_most_one_leader_per_term(self, n_nodes: int, seed: int) -> None:
        c = _cluster(n_nodes, seed)
        c.run_until_leader(max_ticks=2000)
        # Collect (term, leader) pairs — at most one leader per term
        by_term: dict[int, list[str]] = {}
        for nid, node in c.nodes.items():
            if node.state == NodeState.LEADER:
                t = node.current_term
                by_term.setdefault(t, []).append(nid)
        for term, ldrs in by_term.items():
            assert len(ldrs) <= 1, f"Multiple leaders in term {term}: {ldrs}"

    @given(
        st.integers(min_value=3, max_value=5).filter(lambda n: n % 2 == 1),
        st.integers(min_value=0, max_value=49),
    )
    @settings(max_examples=20)
    def test_log_matching_property(self, n_nodes: int, seed: int) -> None:
        """If two logs have an entry with the same (term, index), all preceding entries match."""
        c = _cluster(n_nodes, seed)
        c.run_until_leader(max_ticks=2000)
        for i in range(3):
            c.write(f"SET k{i} v{i}")
        c.replicate(300)
        # Compare logs pairwise
        logs = [(nid, n.log) for nid, n in c.nodes.items()]
        for i in range(len(logs)):
            for j in range(i + 1, len(logs)):
                _, la = logs[i]
                _, lb = logs[j]
                min_len = min(len(la), len(lb))
                for k in range(min_len):
                    if la[k].term == lb[k].term and la[k].index == lb[k].index:
                        # All entries up to k must match
                        for m in range(k):
                            assert la[m].command == lb[m].command

    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=0, max_value=49),
    )
    @settings(max_examples=30)
    def test_terms_are_monotonically_increasing(self, n_writes: int, seed: int) -> None:
        c = _cluster(3, seed)
        c.run_until_leader(max_ticks=2000)
        for i in range(n_writes):
            c.write(f"SET k{i} v{i}")
        c.replicate(300)
        for node in c.nodes.values():
            terms = [e.term for e in node.log]
            assert terms == sorted(terms), f"Non-monotonic terms: {terms}"

    @given(st.integers(min_value=0, max_value=29))
    @settings(max_examples=20)
    def test_committed_entries_durable_after_heal(self, seed: int) -> None:
        """Entries committed before a partition survive after heal."""
        c = _cluster(3, seed)
        c.run_until_leader(max_ticks=2000)
        c.write("SET durable_key committed_value")
        c.replicate(300)

        ldr = c.leader()
        if ldr is None:
            return
        # Partition a follower and heal
        followers = [n for n in c.nodes if n != ldr]
        if not followers:
            return
        c.partition(followers[0])
        c.tick(200)
        c.heal(followers[0])
        c.tick(500)

        # The committed entry must still be on the healed follower
        assert c.nodes[followers[0]].kv.get("durable_key") == "committed_value"
