"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from amlgraph.graph import TransactionGraph
from amlgraph.io_jsonl import account_from_dict, account_to_dict, txn_from_dict, txn_to_dict
from amlgraph.patterns import detect_fan_out
from amlgraph.schema import RiskFlag

from ._fixtures import make_account, make_txn, t_at


@given(amount=st.integers(min_value=1, max_value=10**11))
def test_txn_round_trips_through_dict(amount):
    t = make_txn(amount=amount)
    assert txn_from_dict(txn_to_dict(t)) == t


@given(flags=st.lists(st.sampled_from(list(RiskFlag)), min_size=0, max_size=3, unique=True))
def test_account_round_trips(flags):
    a = make_account(risk_flags=tuple(flags))
    assert account_from_dict(account_to_dict(a)) == a


@given(n=st.integers(min_value=0, max_value=20))
def test_graph_adding_unique_txns_never_raises(n):
    g = TransactionGraph()
    for i in range(n):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst=f"B-{i}", occurred_at=t_at(i)))
    assert g.n_transactions == n


@given(
    min_dests=st.integers(min_value=2, max_value=10), n_txns=st.integers(min_value=0, max_value=15)
)
def test_fan_out_only_fires_above_threshold(min_dests, n_txns):
    """Property: if you have < min_distinct_dests unique destinations from one source, fan-out is silent."""
    g = TransactionGraph()
    for i in range(n_txns):
        # All same destination → never enough distinct dests.
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst="B", occurred_at=t_at(i)))
    alerts = detect_fan_out(g, min_distinct_dests=min_dests)
    assert alerts == []
