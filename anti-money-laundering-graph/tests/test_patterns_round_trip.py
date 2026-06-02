"""Round-trip / cycle detector tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import detect_round_trips

from ._fixtures import make_txn, t_at


def test_no_cycle_no_alert():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    assert detect_round_trips(g) == []


def test_three_node_cycle_fires():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="A", occurred_at=t_at(120)))
    alerts = detect_round_trips(g)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.kind is AlertKind.ROUND_TRIP
    assert a.primary_account == "A"
    assert "A → B → C → A" in a.detail


def test_two_node_cycle_fires():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="A", occurred_at=t_at(60)))
    alerts = detect_round_trips(g)
    assert len(alerts) == 1


def test_cycle_outside_window_not_reported():
    """B → A happens after window expires from the first hop."""
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="A", occurred_at=t_at(100_000)))
    alerts = detect_round_trips(g, window_seconds=60)
    assert alerts == []


def test_max_depth_caps_search():
    """A → B → C → D → A is a 4-hop cycle. With max_depth=2 it's not findable."""
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="C", occurred_at=t_at(60)))
    g.add_transaction(make_txn(txn_id="T3", src="C", dst="D", occurred_at=t_at(120)))
    g.add_transaction(make_txn(txn_id="T4", src="D", dst="A", occurred_at=t_at(180)))
    alerts = detect_round_trips(g, max_depth=2)
    assert alerts == []


def test_rejects_bad_max_depth():
    with pytest.raises(ValueError):
        detect_round_trips(TransactionGraph(), max_depth=1)


def test_emits_one_alert_per_source():
    """Multiple cycles starting at A → still one alert per source."""
    g = TransactionGraph()
    # Cycle 1: A → B → A
    g.add_transaction(make_txn(txn_id="T1", src="A", dst="B", occurred_at=t_at(0)))
    g.add_transaction(make_txn(txn_id="T2", src="B", dst="A", occurred_at=t_at(60)))
    # Cycle 2: A → C → A
    g.add_transaction(make_txn(txn_id="T3", src="A", dst="C", occurred_at=t_at(120)))
    g.add_transaction(make_txn(txn_id="T4", src="C", dst="A", occurred_at=t_at(180)))
    alerts = detect_round_trips(g)
    primaries = {a.primary_account for a in alerts}
    assert primaries == {"A"}
