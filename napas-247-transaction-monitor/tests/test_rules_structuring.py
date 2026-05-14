"""StructuringRule (smurfing) tests."""

from __future__ import annotations

import pytest

from n247mon.alerts import AlertKind
from n247mon.rules import StructuringRule

from ._fixtures import make_txn, t_at


def test_structuring_fires_after_min_count_near_threshold():
    rule = StructuringRule(window_seconds=3600, min_count=3)
    rule.consume(make_txn(amount=9_800_000, occurred_at=t_at(0), txn_id="T0"))
    rule.consume(make_txn(amount=9_700_000, occurred_at=t_at(60), txn_id="T1"))
    alerts = rule.consume(make_txn(amount=9_900_000, occurred_at=t_at(120), txn_id="T2"))
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.STRUCTURING_SUSPECTED


def test_structuring_does_not_fire_for_small_amounts():
    rule = StructuringRule()
    for i in range(5):
        assert rule.consume(make_txn(amount=500_000, occurred_at=t_at(i), txn_id=f"T{i}")) == []


def test_structuring_does_not_fire_for_amounts_far_below_threshold():
    """8M is below the (threshold - margin) = 9.5M cutoff and isn't tracked."""
    rule = StructuringRule()
    for i in range(5):
        assert rule.consume(make_txn(amount=8_000_000, occurred_at=t_at(i), txn_id=f"T{i}")) == []


def test_structuring_does_not_fire_for_amounts_over_threshold():
    """11M is above the 10M threshold and not 'just under'."""
    rule = StructuringRule()
    for i in range(5):
        assert rule.consume(make_txn(amount=11_000_000, occurred_at=t_at(i), txn_id=f"T{i}")) == []


def test_structuring_window_eviction():
    rule = StructuringRule(window_seconds=60, min_count=3)
    rule.consume(make_txn(amount=9_800_000, occurred_at=t_at(0), txn_id="T0"))
    rule.consume(make_txn(amount=9_800_000, occurred_at=t_at(30), txn_id="T1"))
    # T0 is now 70s old → evicted from window. Window has [T1, T2] = 2 entries, no alert.
    alerts = rule.consume(make_txn(amount=9_800_000, occurred_at=t_at(70), txn_id="T2"))
    assert alerts == []


def test_structuring_per_account():
    rule = StructuringRule()
    rule.consume(make_txn(initiator="ACC-A", amount=9_800_000, occurred_at=t_at(0), txn_id="A0"))
    rule.consume(make_txn(initiator="ACC-A", amount=9_700_000, occurred_at=t_at(60), txn_id="A1"))
    # ACC-B is fresh.
    assert (
        rule.consume(
            make_txn(initiator="ACC-B", amount=9_800_000, occurred_at=t_at(120), txn_id="B0")
        )
        == []
    )


def test_structuring_rejects_bad_config():
    with pytest.raises(ValueError):
        StructuringRule(window_seconds=0)
    with pytest.raises(ValueError):
        StructuringRule(min_count=1)
    with pytest.raises(ValueError):
        StructuringRule(margin_vnd=0)
    with pytest.raises(ValueError):
        StructuringRule(margin_vnd=10_000_000)  # equals threshold


def test_structuring_exactly_at_threshold_counts():
    """10M (== threshold) is in the tracked range."""
    rule = StructuringRule(window_seconds=3600, min_count=3)
    rule.consume(make_txn(amount=10_000_000, occurred_at=t_at(0), txn_id="T0"))
    rule.consume(make_txn(amount=10_000_000, occurred_at=t_at(60), txn_id="T1"))
    alerts = rule.consume(make_txn(amount=10_000_000, occurred_at=t_at(120), txn_id="T2"))
    assert len(alerts) == 1
