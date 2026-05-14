"""Structured-deposit detector tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import detect_structured_deposits

from ._fixtures import make_txn, t_at


def test_fires_on_classic_smurfing():
    g = TransactionGraph()
    for i in range(4):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=9_800_000,
                occurred_at=t_at(i * 60),
            )
        )
    alerts = detect_structured_deposits(g)
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.STRUCTURED_DEPOSIT
    assert alerts[0].primary_account == "D"


def test_does_not_fire_with_one_source():
    """3 incoming txns from a single source is NOT a structuring pattern (per-recipient view)."""
    g = TransactionGraph()
    for i in range(3):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src="A",
                dst="D",
                amount=9_800_000,
                occurred_at=t_at(i * 60),
            )
        )
    alerts = detect_structured_deposits(g, min_distinct_sources=2)
    assert alerts == []


def test_does_not_fire_for_amounts_outside_band():
    g = TransactionGraph()
    for i in range(4):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=5_000_000,
                occurred_at=t_at(i * 60),
            )
        )
    assert detect_structured_deposits(g) == []


def test_fires_at_exact_threshold():
    """10M (== threshold) is in the tracked range."""
    g = TransactionGraph()
    for i in range(3):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=10_000_000,
                occurred_at=t_at(i * 60),
            )
        )
    alerts = detect_structured_deposits(g)
    assert len(alerts) == 1


def test_does_not_fire_above_threshold():
    g = TransactionGraph()
    for i in range(4):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=11_000_000,
                occurred_at=t_at(i * 60),
            )
        )
    assert detect_structured_deposits(g) == []


def test_window_eviction():
    g = TransactionGraph()
    for i in range(4):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=9_800_000,
                occurred_at=t_at(i * 3600),
            )
        )
    assert detect_structured_deposits(g, window_seconds=60) == []


def test_total_amount_summed():
    g = TransactionGraph()
    for i in range(3):
        g.add_transaction(
            make_txn(
                txn_id=f"T-{i}",
                src=f"A{i}",
                dst="D",
                amount=9_700_000,
                occurred_at=t_at(i * 60),
            )
        )
    alerts = detect_structured_deposits(g)
    assert alerts[0].total_amount_vnd == 29_100_000


def test_rejects_bad_config():
    with pytest.raises(ValueError):
        detect_structured_deposits(TransactionGraph(), margin_vnd=0)
    with pytest.raises(ValueError):
        detect_structured_deposits(TransactionGraph(), margin_vnd=10_000_000)
    with pytest.raises(ValueError):
        detect_structured_deposits(TransactionGraph(), min_count=1)
