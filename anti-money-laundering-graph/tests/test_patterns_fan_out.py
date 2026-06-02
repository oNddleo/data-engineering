"""Fan-out detector tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import detect_fan_out

from ._fixtures import make_txn, t_at


def test_no_alert_below_min_distinct_dests():
    g = TransactionGraph()
    for i in range(3):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", occurred_at=t_at(i)))
    alerts = detect_fan_out(g, min_distinct_dests=5)
    assert alerts == []


def test_alert_when_six_distinct_dests_in_window():
    g = TransactionGraph()
    for i in range(6):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", occurred_at=t_at(i * 60)))
    alerts = detect_fan_out(g, min_distinct_dests=5, window_seconds=600)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.kind is AlertKind.FAN_OUT
    assert a.primary_account == "A"
    assert len(a.related_accounts) == 6


def test_window_evicts_spread_destinations():
    """If the 5+ destinations are spread across a wider span than window, no alert."""
    g = TransactionGraph()
    for i in range(6):
        g.add_transaction(
            make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", occurred_at=t_at(i * 3600))
        )
    alerts = detect_fan_out(g, min_distinct_dests=5, window_seconds=1800)
    assert alerts == []


def test_repeated_dest_does_not_count_twice():
    g = TransactionGraph()
    for i in range(8):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst="B", occurred_at=t_at(i)))
    alerts = detect_fan_out(g, min_distinct_dests=5)
    assert alerts == []


def test_emits_at_most_one_alert_per_source():
    g = TransactionGraph()
    for i in range(10):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", occurred_at=t_at(i * 60)))
    alerts = detect_fan_out(g, min_distinct_dests=5, window_seconds=3600)
    assert len(alerts) == 1


def test_total_amount_reported():
    g = TransactionGraph()
    for i in range(5):
        g.add_transaction(
            make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", amount=1_000_000, occurred_at=t_at(i))
        )
    alerts = detect_fan_out(g, min_distinct_dests=5)
    assert len(alerts) == 1
    assert alerts[0].total_amount_vnd == 5_000_000


def test_detects_multiple_sources_independently():
    g = TransactionGraph()
    for src_idx, src in enumerate(["A", "B"]):
        for i in range(5):
            g.add_transaction(
                make_txn(
                    txn_id=f"{src}-{i}",
                    src=src,
                    dst=f"{src}-D{i}",
                    occurred_at=t_at(src_idx * 7200 + i * 60),
                )
            )
    alerts = detect_fan_out(g, min_distinct_dests=5)
    primaries = {a.primary_account for a in alerts}
    assert primaries == {"A", "B"}


def test_rejects_bad_config():
    g = TransactionGraph()
    with pytest.raises(ValueError):
        detect_fan_out(g, min_distinct_dests=1)
