"""Simulator + anomaly-injection tests."""

from __future__ import annotations

import pytest

from n247mon.alerts import AlertKind
from n247mon.engine import MonitorEngine
from n247mon.rules import BiometricRule, BlacklistRule, StructuringRule, VelocityRule
from n247mon.simulator import generate


def test_generate_reproducible_with_seed():
    a = generate(n_txns=20, seed=42)
    b = generate(n_txns=20, seed=42)
    assert [t.txn_id for t in a] == [t.txn_id for t in b]
    assert [t.amount_vnd for t in a] == [t.amount_vnd for t in b]


def test_generate_different_seed_different_output():
    a = generate(n_txns=20, seed=1)
    b = generate(n_txns=20, seed=2)
    # At least some difference (amounts or initiators).
    assert [t.amount_vnd for t in a] != [t.amount_vnd for t in b]


def test_generate_output_sorted_by_occurred_at():
    txns = generate(n_txns=50, seed=0)
    assert all(txns[i].occurred_at <= txns[i + 1].occurred_at for i in range(len(txns) - 1))


def test_generate_zero_txns_with_no_anomalies_is_empty():
    assert generate(n_txns=0) == []


def test_inject_bio_single_triggers_biometric_rule():
    txns = generate(n_txns=5, seed=0, inject_anomalies=["bio_single"])
    eng = MonitorEngine(rules=[BiometricRule()])
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.BIO_REQUIRED_SINGLE_TXN in kinds


def test_inject_bio_cumulative_triggers_cumulative_rule():
    txns = generate(n_txns=0, seed=0, inject_anomalies=["bio_cumulative"])
    eng = MonitorEngine(rules=[BiometricRule()])
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.BIO_REQUIRED_CUMULATIVE in kinds


def test_inject_velocity_triggers_velocity_rule():
    txns = generate(n_txns=0, seed=0, inject_anomalies=["velocity"])
    eng = MonitorEngine(rules=[VelocityRule(window_seconds=60, threshold=10)])
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.VELOCITY_SPIKE in kinds


def test_inject_structuring_triggers_structuring_rule():
    txns = generate(n_txns=0, seed=0, inject_anomalies=["structuring"])
    eng = MonitorEngine(rules=[StructuringRule()])
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.STRUCTURING_SUSPECTED in kinds


def test_inject_blacklist_triggers_blacklist_rule():
    bl = ["BAD-001", "BAD-002"]
    txns = generate(n_txns=0, seed=0, inject_anomalies=["blacklist"], blacklist=bl)
    eng = MonitorEngine(rules=[BlacklistRule(set(bl))])
    alerts = eng.consume_many(txns)
    kinds = {a.kind for a in alerts}
    assert AlertKind.BLACKLIST_HIT in kinds


def test_inject_unknown_anomaly_raises():
    with pytest.raises(ValueError):
        generate(n_txns=5, inject_anomalies=["meteor_strike"])


def test_generate_with_baseline_only_uses_valid_bins():
    """Every txn in the synthetic stream uses a registered NAPAS BIN."""
    from n247mon.banks import BIN_TO_BANK

    txns = generate(n_txns=50, seed=0)
    valid = set(BIN_TO_BANK)
    for t in txns:
        assert t.initiator_bank_bin in valid
        assert t.beneficiary_bank_bin in valid


def test_generate_baseline_amount_positive():
    txns = generate(n_txns=100, seed=0)
    assert all(t.amount_vnd > 0 for t in txns)
