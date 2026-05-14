"""Fan-in detector tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import detect_fan_in

from ._fixtures import make_txn, t_at


def test_no_alert_below_threshold():
    g = TransactionGraph()
    for i in range(3):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src=f"A{i}", dst="D", occurred_at=t_at(i)))
    assert detect_fan_in(g, min_distinct_sources=5) == []


def test_alert_when_many_sources():
    g = TransactionGraph()
    for i in range(6):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src=f"A{i}", dst="D", occurred_at=t_at(i * 60)))
    alerts = detect_fan_in(g, min_distinct_sources=5, window_seconds=600)
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.FAN_IN
    assert alerts[0].primary_account == "D"


def test_repeated_source_does_not_count_twice():
    g = TransactionGraph()
    for i in range(8):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst="D", occurred_at=t_at(i)))
    assert detect_fan_in(g, min_distinct_sources=5) == []


def test_window_evicts_spread_sources():
    g = TransactionGraph()
    for i in range(6):
        g.add_transaction(
            make_txn(txn_id=f"T-{i}", src=f"A{i}", dst="D", occurred_at=t_at(i * 3600))
        )
    assert detect_fan_in(g, min_distinct_sources=5, window_seconds=1800) == []


def test_rejects_bad_config():
    with pytest.raises(ValueError):
        detect_fan_in(TransactionGraph(), min_distinct_sources=1)


def test_total_amount():
    g = TransactionGraph()
    for i in range(5):
        g.add_transaction(
            make_txn(txn_id=f"T-{i}", src=f"A{i}", dst="D", amount=2_000_000, occurred_at=t_at(i))
        )
    alerts = detect_fan_in(g, min_distinct_sources=5)
    assert alerts[0].total_amount_vnd == 10_000_000
