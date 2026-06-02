"""Simulator tests."""

from __future__ import annotations

from sbv2345.schema import TriggerKind
from sbv2345.simulator import generate
from sbv2345.triggers import Classifier


def test_generate_reproducible_with_seed():
    a = generate(seed=42)
    b = generate(seed=42)
    assert [t.txn_id for t in a] == [t.txn_id for t in b]


def test_generate_sorted_by_occurred_at():
    txns = generate(seed=0)
    assert all(txns[i].occurred_at <= txns[i + 1].occurred_at for i in range(len(txns) - 1))


def test_generate_small_only_yields_no_audit_events():
    """If only n_small > 0, the classifier should find nothing to audit."""
    c = Classifier()
    txns = generate(seed=1, n_small=20, n_large=0, n_cumulative_pair=0, n_cross_border=0)
    audited = sum(1 for t in txns if c.classify(t) is not None)
    assert audited == 0


def test_generate_large_yields_single_trigger():
    c = Classifier()
    txns = generate(seed=1, n_small=0, n_large=3, n_cumulative_pair=0, n_cross_border=0)
    events = [e for t in txns if (e := c.classify(t)) is not None]
    assert len(events) == 3
    for e in events:
        assert TriggerKind.SINGLE_TXN_OVER_10M in e.triggered_kinds


def test_generate_cumulative_yields_one_audit_per_pair():
    c = Classifier()
    txns = generate(seed=1, n_small=0, n_large=0, n_cumulative_pair=2, n_cross_border=0)
    events = [e for t in txns if (e := c.classify(t)) is not None]
    # Each pair triggers once (on the second member).
    assert sum(1 for e in events if TriggerKind.DAILY_CUMULATIVE_OVER_20M in e.triggered_kinds) >= 2


def test_generate_cross_border_fires():
    c = Classifier()
    txns = generate(seed=1, n_small=0, n_large=0, n_cumulative_pair=0, n_cross_border=3)
    events = [e for t in txns if (e := c.classify(t)) is not None]
    assert all(TriggerKind.INTERNATIONAL_TRANSFER in e.triggered_kinds for e in events)


def test_generate_high_risk_beneficiary():
    bl = ["BAD-001"]
    c = Classifier(high_risk_accounts=bl)
    txns = generate(
        seed=1,
        n_small=0,
        n_large=0,
        n_cumulative_pair=0,
        n_cross_border=0,
        n_high_risk_beneficiary=1,
        high_risk_accounts=bl,
    )
    events = [e for t in txns if (e := c.classify(t)) is not None]
    assert any(TriggerKind.HIGH_RISK_BENEFICIARY in e.triggered_kinds for e in events)


def test_generate_full_mix_count_lower_bound():
    txns = generate(seed=0)
    # Default counts: small=50, large=5, cumulative=2*2=4, cross_border=2 → ≥ 61.
    assert len(txns) >= 61
