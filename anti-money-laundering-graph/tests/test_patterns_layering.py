"""Layering chain detector tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import detect_layering_chains

from ._fixtures import make_txn, t_at


def test_short_chain_no_alert():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    assert detect_layering_chains(g, min_depth=3) == []


def test_three_hop_chain_fires():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="D", occurred_at=t_at(120)))
    alerts = detect_layering_chains(g, min_depth=3)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.kind is AlertKind.LAYERING_CHAIN
    assert a.primary_account == "A"
    assert "A → B → C → D" in a.detail


def test_chain_with_late_hop_violating_hop_seconds_not_fired():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    # 7200s gap → exceeds default hop_seconds=1800
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="D", occurred_at=t_at(7320)))
    alerts = detect_layering_chains(g, min_depth=3, hop_seconds=1800)
    assert alerts == []


def test_cycle_not_revisited():
    """A path can't loop back through the same intermediary."""
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="A", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="A", dst="B", occurred_at=t_at(120)))
    # Can't make a 3-hop chain without revisiting either A or B.
    alerts = detect_layering_chains(g, min_depth=3)
    assert alerts == []


def test_emits_one_alert_per_source_max():
    """Even if two different chains start at A, we report one."""
    g = TransactionGraph()
    # Chain 1: A → B → C → D
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="D", occurred_at=t_at(120)))
    # Chain 2: A → E → F → G
    g.add_transaction(make_txn(txn_id="T4", src="A", dst="E", occurred_at=t_at(200)))
    g.add_transaction(make_txn(txn_id="T5", src="E", dst="F", occurred_at=t_at(260)))
    g.add_transaction(make_txn(txn_id="T6", src="F", dst="G", occurred_at=t_at(320)))
    alerts = detect_layering_chains(g, min_depth=3)
    primaries = {a.primary_account for a in alerts}
    assert primaries == {"A"}


def test_rejects_bad_min_depth():
    with pytest.raises(ValueError):
        detect_layering_chains(TransactionGraph(), min_depth=1)


def test_total_seconds_caps_walk():
    """Cumulative duration > total_seconds → walk doesn't qualify."""
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="D", occurred_at=t_at(120)))
    # Total span 0 → 120s. With total_seconds=60, walk should not complete.
    alerts = detect_layering_chains(g, min_depth=3, total_seconds=60)
    assert alerts == []


def test_amount_carried_on_first_hop():
    g = TransactionGraph()
    g.add_transaction(
        make_txn(txn_id="T1", src="A", dst="B", amount=5_000_000, occurred_at=t_at(0))
    )
    g.add_transaction(
        make_txn(txn_id="T2", src="B", dst="C", amount=4_900_000, occurred_at=t_at(60))
    )
    g.add_transaction(
        make_txn(txn_id="T3", src="C", dst="D", amount=4_800_000, occurred_at=t_at(120))
    )
    alerts = detect_layering_chains(g, min_depth=3)
    assert alerts[0].total_amount_vnd == 5_000_000
