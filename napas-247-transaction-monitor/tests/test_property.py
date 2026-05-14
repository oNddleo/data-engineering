"""Hypothesis property tests — invariants over arbitrary inputs."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from n247mon.engine import MonitorEngine
from n247mon.io_jsonl import txn_from_dict, txn_to_dict
from n247mon.rules import BiometricRule, BlacklistRule, VelocityRule
from n247mon.schema import VN_TZ

from ._fixtures import make_txn


@given(amount=st.integers(min_value=10_000_001, max_value=10**12))
def test_any_above_10m_without_bio_fires_single(amount):
    """Property: any txn > 10M VND with biometric=False fires BIO_REQUIRED_SINGLE_TXN."""
    rule = BiometricRule()
    alerts = rule.consume(make_txn(amount=amount, biometric=False))
    assert len(alerts) == 1


@given(amount=st.integers(min_value=1, max_value=10_000_000))
def test_below_threshold_with_bio_never_fires(amount):
    """Property: anything ≤ 10M with biometric=True never fires (single rule)."""
    rule = BiometricRule()
    alerts = rule.consume(make_txn(amount=amount, biometric=True))
    assert alerts == []


@given(
    bl_size=st.integers(min_value=0, max_value=50),
    is_member=st.booleans(),
)
def test_blacklist_fires_iff_member(bl_size, is_member):
    bl = {f"BAD-{i:03d}" for i in range(bl_size)}
    beneficiary = "BAD-000" if (is_member and bl_size > 0) else "GOOD-001"
    rule = BlacklistRule(bl)
    alerts = rule.consume(make_txn(beneficiary=beneficiary))
    if is_member and bl_size > 0:
        assert len(alerts) == 1
    else:
        assert alerts == []


@given(n=st.integers(min_value=1, max_value=20))
def test_velocity_at_or_below_threshold_silent(n):
    """If we send exactly ``n`` ≤ threshold txns, no alert fires."""
    threshold = max(n, 5)
    rule = VelocityRule(window_seconds=60, threshold=threshold)
    alerts: list = []
    base = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)
    for i in range(n):
        alerts.extend(
            rule.consume(make_txn(occurred_at=base + timedelta(seconds=i), txn_id=f"T{i}"))
        )
    assert alerts == []


@given(amount=st.integers(min_value=1, max_value=10**10))
def test_txn_round_trips_through_jsonl(amount):
    t = make_txn(amount=amount)
    assert txn_from_dict(txn_to_dict(t)) == t


@given(n=st.integers(min_value=0, max_value=50))
def test_engine_stats_match_alert_count(n):
    """Property: stats.alerts_fired == len(returned alerts) over all txns."""
    rule = BiometricRule()
    eng = MonitorEngine(rules=[rule])
    base = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)
    all_alerts: list = []
    for i in range(n):
        all_alerts.extend(
            eng.consume(
                make_txn(
                    amount=50_000_000,
                    biometric=False,
                    txn_id=f"T{i}",
                    occurred_at=base + timedelta(seconds=i),
                )
            )
        )
    assert eng.stats.alerts_fired == len(all_alerts)
    assert eng.stats.txns_seen == n
