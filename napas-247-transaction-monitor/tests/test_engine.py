"""MonitorEngine orchestration tests."""

from __future__ import annotations

import pytest

from n247mon.alerts import AlertKind, Severity
from n247mon.engine import MonitorEngine
from n247mon.rules import BiometricRule, BlacklistRule, StructuringRule, VelocityRule

from ._fixtures import make_txn, t_at


def test_engine_requires_at_least_one_rule():
    with pytest.raises(ValueError):
        MonitorEngine(rules=[])


def test_engine_consume_single_txn_no_alerts():
    eng = MonitorEngine(rules=[BiometricRule(), BlacklistRule(set())])
    alerts = eng.consume(make_txn(amount=1_000_000, biometric=True))
    assert alerts == []
    assert eng.stats.txns_seen == 1
    assert eng.stats.alerts_fired == 0


def test_engine_fires_biometric_alert():
    eng = MonitorEngine(rules=[BiometricRule()])
    alerts = eng.consume(make_txn(amount=50_000_000, biometric=False))
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.BIO_REQUIRED_SINGLE_TXN
    assert eng.stats.alerts_fired == 1
    assert eng.stats.alerts_by_kind[AlertKind.BIO_REQUIRED_SINGLE_TXN] == 1


def test_engine_fires_multiple_rules_for_same_txn():
    """A txn can violate >1 rule and the engine returns all alerts."""
    eng = MonitorEngine(
        rules=[
            BiometricRule(),
            BlacklistRule({"BAD-001"}),
        ]
    )
    alerts = eng.consume(make_txn(amount=50_000_000, biometric=False, beneficiary="BAD-001"))
    kinds = {a.kind for a in alerts}
    assert AlertKind.BIO_REQUIRED_SINGLE_TXN in kinds
    assert AlertKind.BLACKLIST_HIT in kinds


def test_engine_consume_many_returns_in_order():
    eng = MonitorEngine(rules=[BiometricRule()])
    txns = [
        make_txn(amount=50_000_000, biometric=False, txn_id="T0", occurred_at=t_at(0)),
        make_txn(amount=1_000_000, biometric=True, txn_id="T1", occurred_at=t_at(1)),
        make_txn(amount=60_000_000, biometric=False, txn_id="T2", occurred_at=t_at(2)),
    ]
    alerts = eng.consume_many(txns)
    assert [a.txn_id for a in alerts] == ["T0", "T2"]


def test_engine_stats_severity_breakdown():
    eng = MonitorEngine(rules=[BiometricRule(), BlacklistRule({"BAD-001"})])
    eng.consume(make_txn(amount=50_000_000, biometric=False, beneficiary="BAD-001"))
    assert eng.stats.alerts_by_severity[Severity.CRIT] == 2


def test_engine_rules_property_returns_copy():
    """Engine.rules must not let callers mutate the internal list."""
    bio = BiometricRule()
    eng = MonitorEngine(rules=[bio])
    rules = eng.rules
    rules.append(BlacklistRule(set()))
    assert len(eng.rules) == 1  # internal list unchanged


def test_engine_full_stack_smoke():
    eng = MonitorEngine(
        rules=[
            BiometricRule(),
            VelocityRule(window_seconds=60, threshold=5),
            StructuringRule(window_seconds=3600, min_count=3),
            BlacklistRule({"BAD-001"}),
        ]
    )
    txns = [
        make_txn(amount=9_800_000, biometric=False, txn_id="S0", occurred_at=t_at(0)),
        make_txn(amount=9_700_000, biometric=False, txn_id="S1", occurred_at=t_at(60)),
        make_txn(amount=9_900_000, biometric=False, txn_id="S2", occurred_at=t_at(120)),
        make_txn(
            amount=2_000_000,
            biometric=True,
            beneficiary="BAD-001",
            txn_id="B0",
            occurred_at=t_at(180),
        ),
    ]
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.STRUCTURING_SUSPECTED in kinds
    assert AlertKind.BLACKLIST_HIT in kinds
