"""BiometricRule (Decision 2345/QĐ-NHNN) tests."""

from __future__ import annotations

from n247mon.alerts import AlertKind, Severity
from n247mon.rules import BiometricRule

from ._fixtures import make_txn, t_at


def test_small_txn_without_bio_no_alert():
    rule = BiometricRule()
    txn = make_txn(amount=500_000, biometric=False)
    assert rule.consume(txn) == []


def test_small_txn_with_bio_no_alert():
    rule = BiometricRule()
    txn = make_txn(amount=500_000, biometric=True)
    assert rule.consume(txn) == []


def test_single_txn_over_10m_without_bio_fires():
    rule = BiometricRule()
    txn = make_txn(amount=10_500_000, biometric=False, txn_id="T1")
    alerts = rule.consume(txn)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.kind is AlertKind.BIO_REQUIRED_SINGLE_TXN
    assert a.severity is Severity.CRIT
    assert a.amount_vnd == 10_500_000


def test_single_txn_exactly_10m_does_not_fire():
    """Decision 2345 says '> 10 triệu' (strictly more than)."""
    rule = BiometricRule()
    txn = make_txn(amount=10_000_000, biometric=False)
    assert rule.consume(txn) == []


def test_single_txn_over_10m_with_bio_no_alert():
    rule = BiometricRule()
    txn = make_txn(amount=50_000_000, biometric=True)
    assert rule.consume(txn) == []


def test_cumulative_pushes_over_20m_fires():
    rule = BiometricRule()
    # Three 8M transfers from the same account on the same day:
    # 8M + 8M = 16M (no alert), + 8M = 24M (> 20M, third one without bio fires CUMULATIVE).
    assert (
        rule.consume(make_txn(amount=8_000_000, biometric=False, txn_id="A", occurred_at=t_at(0)))
        == []
    )
    assert (
        rule.consume(make_txn(amount=8_000_000, biometric=False, txn_id="B", occurred_at=t_at(10)))
        == []
    )
    alerts = rule.consume(
        make_txn(amount=8_000_000, biometric=False, txn_id="C", occurred_at=t_at(20))
    )
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.BIO_REQUIRED_CUMULATIVE


def test_cumulative_with_bio_no_alert():
    rule = BiometricRule()
    for i, bio in enumerate([False, False, True]):
        alerts = rule.consume(
            make_txn(amount=8_000_000, biometric=bio, txn_id=f"T{i}", occurred_at=t_at(i))
        )
        if i == 2:
            # Third txn has bio, so no CUMULATIVE alert even though total > 20M.
            assert alerts == []
        else:
            assert alerts == []


def test_cumulative_resets_at_day_boundary():
    rule = BiometricRule()
    # Two 8M txns on day 1, then 8M on day 2 — day 2's first txn should not fire.
    rule.consume(make_txn(amount=8_000_000, biometric=False, occurred_at=t_at(0), txn_id="A"))
    rule.consume(make_txn(amount=8_000_000, biometric=False, occurred_at=t_at(10), txn_id="B"))
    # Day 2.
    from datetime import datetime

    from n247mon.schema import VN_TZ

    day2 = datetime(2026, 5, 15, 9, 0, tzinfo=VN_TZ)
    alerts = rule.consume(make_txn(amount=8_000_000, biometric=False, occurred_at=day2, txn_id="C"))
    assert alerts == []


def test_cumulative_is_per_account():
    """Daily totals are tracked per initiator account, not globally."""
    rule = BiometricRule()
    rule.consume(make_txn(initiator="ACC-1", amount=15_000_000, biometric=True, txn_id="A"))
    # ACC-2 has its own counter; this small txn shouldn't trigger CUMULATIVE
    # just because ACC-1 already crossed 20M (it hasn't, but even if it had).
    alerts = rule.consume(make_txn(initiator="ACC-2", amount=500_000, biometric=False, txn_id="B"))
    assert alerts == []


def test_large_txn_does_not_double_alert():
    """A single 30M txn without bio fires SINGLE only, not also CUMULATIVE."""
    rule = BiometricRule()
    alerts = rule.consume(make_txn(amount=30_000_000, biometric=False))
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.BIO_REQUIRED_SINGLE_TXN


def test_cumulative_only_fires_when_already_over_20m_but_this_txn_small():
    """Once an account is past 20M, every subsequent small txn without bio fires CUMULATIVE."""
    rule = BiometricRule()
    # Push the account past 20M with one big bio'd txn.
    rule.consume(make_txn(amount=25_000_000, biometric=True, txn_id="A", occurred_at=t_at(0)))
    # Next 1M txn without bio should fire CUMULATIVE.
    alerts = rule.consume(
        make_txn(amount=1_000_000, biometric=False, txn_id="B", occurred_at=t_at(10))
    )
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.BIO_REQUIRED_CUMULATIVE
