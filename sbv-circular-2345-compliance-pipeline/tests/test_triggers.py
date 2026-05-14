"""Classifier rule tests — Decision 2345 trigger semantics."""

from __future__ import annotations

from datetime import datetime

from sbv2345.schema import VN_TZ, TriggerKind
from sbv2345.triggers import LEGAL_BASIS, Classifier

from ._fixtures import make_txn, t_at


def test_small_txn_no_trigger_returns_none():
    c = Classifier()
    assert c.classify(make_txn(amount=500_000)) is None


def test_small_txn_with_bio_no_trigger():
    """Auth method shouldn't change the trigger — auth is observed, not gated by us."""
    from sbv2345.schema import AuthMethod, BiometricMethod

    c = Classifier()
    assert (
        c.classify(
            make_txn(
                amount=500_000,
                auth_method=AuthMethod.BIOMETRIC,
                biometric_method=BiometricMethod.FACE,
            )
        )
        is None
    )


def test_single_over_10m_fires_single_only():
    c = Classifier()
    e = c.classify(make_txn(amount=15_000_000))
    assert e is not None
    assert e.triggered_kinds == (TriggerKind.SINGLE_TXN_OVER_10M,)


def test_exactly_10m_does_not_fire_single():
    """Decision 2345 says '> 10 triệu' (strictly more than)."""
    c = Classifier()
    assert c.classify(make_txn(amount=10_000_000)) is None


def test_cumulative_fires_for_second_pair_under_threshold():
    c = Classifier()
    # 8M (no trigger, total 8M) → 8M (no trigger, total 16M)
    # → 8M (cumulative now 24M > 20M, txn ≤ 10M, fires CUMULATIVE).
    a = c.classify(make_txn(amount=8_000_000, txn_id="A", occurred_at=t_at(0)))
    b = c.classify(make_txn(amount=8_000_000, txn_id="B", occurred_at=t_at(10)))
    third = c.classify(make_txn(amount=8_000_000, txn_id="C", occurred_at=t_at(20)))
    assert a is None
    assert b is None
    assert third is not None
    assert TriggerKind.DAILY_CUMULATIVE_OVER_20M in third.triggered_kinds


def test_cumulative_per_account():
    c = Classifier()
    # ACC-A puts 15M on the books, then ACC-B's first 8M shouldn't trigger.
    c.classify(make_txn(initiator="ACC-A", amount=15_000_000, txn_id="A", occurred_at=t_at(0)))
    e = c.classify(make_txn(initiator="ACC-B", amount=8_000_000, txn_id="B", occurred_at=t_at(10)))
    assert e is None


def test_cumulative_resets_at_day_boundary():
    c = Classifier()
    c.classify(make_txn(amount=15_000_000, txn_id="A", occurred_at=t_at(0)))
    next_day = datetime(2026, 5, 15, 9, 0, tzinfo=VN_TZ)
    # First txn of day 2 should not see day 1's total.
    e = c.classify(make_txn(amount=8_000_000, txn_id="B", occurred_at=next_day))
    assert e is None


def test_high_risk_beneficiary_fires():
    c = Classifier(high_risk_accounts=["BAD-001"])
    e = c.classify(make_txn(amount=500_000, beneficiary="BAD-001"))
    assert e is not None
    assert TriggerKind.HIGH_RISK_BENEFICIARY in e.triggered_kinds


def test_cross_border_fires():
    c = Classifier()
    e = c.classify(make_txn(amount=500_000, cross_border=True))
    assert e is not None
    assert TriggerKind.INTERNATIONAL_TRANSFER in e.triggered_kinds


def test_multiple_triggers_stack():
    c = Classifier(high_risk_accounts=["BAD-001"])
    e = c.classify(make_txn(amount=50_000_000, beneficiary="BAD-001", cross_border=True))
    assert e is not None
    kinds = set(e.triggered_kinds)
    assert TriggerKind.SINGLE_TXN_OVER_10M in kinds
    assert TriggerKind.HIGH_RISK_BENEFICIARY in kinds
    assert TriggerKind.INTERNATIONAL_TRANSFER in kinds


def test_single_does_not_also_fire_cumulative():
    """A single large txn fires SINGLE, not also CUMULATIVE — they're mutually exclusive by design."""
    c = Classifier()
    e = c.classify(make_txn(amount=30_000_000))
    assert e is not None
    assert TriggerKind.SINGLE_TXN_OVER_10M in e.triggered_kinds
    assert TriggerKind.DAILY_CUMULATIVE_OVER_20M not in e.triggered_kinds


def test_legal_bases_populated_per_trigger():
    c = Classifier()
    e = c.classify(make_txn(amount=15_000_000))
    assert e is not None
    assert len(e.legal_bases) == len(e.triggered_kinds)
    assert "Điều 1.1" in e.legal_bases[0]


def test_daily_cumulative_value_carried_on_event():
    c = Classifier()
    c.classify(make_txn(amount=8_000_000, txn_id="A", occurred_at=t_at(0)))
    c.classify(make_txn(amount=8_000_000, txn_id="B", occurred_at=t_at(10)))
    e = c.classify(make_txn(amount=8_000_000, txn_id="C", occurred_at=t_at(20)))
    assert e is not None
    assert e.daily_cumulative_after_vnd == 24_000_000


def test_classifier_daily_total_introspection():
    c = Classifier()
    c.classify(make_txn(amount=8_000_000, occurred_at=t_at(0)))
    c.classify(make_txn(amount=2_000_000, occurred_at=t_at(10)))
    total = c.daily_total("0000000001", t_at(0).date())
    assert total == 10_000_000


def test_legal_basis_map_covers_all_kinds():
    for k in TriggerKind:
        assert k in LEGAL_BASIS
