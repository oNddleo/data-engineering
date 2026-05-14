"""VelocityRule tests."""

from __future__ import annotations

import pytest

from n247mon.alerts import AlertKind, Severity
from n247mon.rules import VelocityRule

from ._fixtures import make_txn, t_at


def test_velocity_below_threshold_no_alert():
    rule = VelocityRule(window_seconds=60, threshold=5)
    for i in range(5):
        assert rule.consume(make_txn(occurred_at=t_at(i), txn_id=f"T{i}")) == []


def test_velocity_crosses_threshold_fires_on_excess():
    rule = VelocityRule(window_seconds=60, threshold=5)
    for i in range(5):
        rule.consume(make_txn(occurred_at=t_at(i), txn_id=f"T{i}"))
    alerts = rule.consume(make_txn(occurred_at=t_at(5), txn_id="T5"))
    assert len(alerts) == 1
    a = alerts[0]
    assert a.kind is AlertKind.VELOCITY_SPIKE
    assert a.severity is Severity.WARN


def test_velocity_window_evicts_old_events():
    rule = VelocityRule(window_seconds=10, threshold=3)
    # 4 events all spaced 5s apart — only the last 3 are in the 10s window
    # at the time of the 4th, so we should be at exactly threshold + 1
    # only if 4th comes before 3 evict. Let's test the eviction explicitly.
    rule.consume(make_txn(occurred_at=t_at(0), txn_id="T0"))
    rule.consume(make_txn(occurred_at=t_at(20), txn_id="T1"))  # 20s later, T0 evicted
    rule.consume(make_txn(occurred_at=t_at(21), txn_id="T2"))
    alerts = rule.consume(make_txn(occurred_at=t_at(22), txn_id="T3"))
    assert alerts == []  # only 3 in window after eviction


def test_velocity_is_per_account():
    rule = VelocityRule(window_seconds=60, threshold=3)
    for i in range(4):
        rule.consume(make_txn(initiator="ACC-A", occurred_at=t_at(i), txn_id=f"A{i}"))
    # ACC-B should still have an empty window.
    assert rule.consume(make_txn(initiator="ACC-B", occurred_at=t_at(0), txn_id="B0")) == []


def test_velocity_rule_rejects_bad_config():
    with pytest.raises(ValueError):
        VelocityRule(window_seconds=0, threshold=5)
    with pytest.raises(ValueError):
        VelocityRule(window_seconds=60, threshold=0)


def test_velocity_alert_carries_correct_amount():
    rule = VelocityRule(window_seconds=60, threshold=2)
    rule.consume(make_txn(occurred_at=t_at(0), txn_id="T0", amount=100_000))
    rule.consume(make_txn(occurred_at=t_at(1), txn_id="T1", amount=200_000))
    alerts = rule.consume(make_txn(occurred_at=t_at(2), txn_id="T2", amount=300_000))
    assert alerts[0].amount_vnd == 300_000
    assert alerts[0].txn_id == "T2"
