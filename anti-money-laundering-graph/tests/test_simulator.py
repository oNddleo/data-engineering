"""Simulator + end-to-end integration tests."""

from __future__ import annotations

from amlgraph.alerts import AlertKind
from amlgraph.graph import TransactionGraph
from amlgraph.patterns import (
    detect_fan_in,
    detect_fan_out,
    detect_layering_chains,
    detect_round_trips,
    detect_structured_deposits,
)
from amlgraph.simulator import generate


def _build_graph(accounts, txns):
    g = TransactionGraph()
    for a in accounts:
        g.add_account(a)
    for t in txns:
        g.add_transaction(t)
    return g


def test_generate_reproducible_with_seed():
    a1 = generate(seed=42)
    a2 = generate(seed=42)
    assert [t.txn_id for t in a1[1]] == [t.txn_id for t in a2[1]]


def test_injection_strictly_increases_alert_count():
    """A noisy baseline can produce false positives; what we care about is that
    injecting an explicit pattern strictly raises the alert count for that
    specific kind compared to the same seed with no injection.
    """
    accounts0, txns0 = generate(seed=11, n_accounts=15, n_normal_txns=15)
    g0 = _build_graph(accounts0, txns0)
    baseline_fan_in = sum(
        1 for a in detect_fan_in(g0, min_distinct_sources=5) if a.kind is AlertKind.FAN_IN
    )

    accounts1, txns1 = generate(seed=11, n_accounts=15, n_normal_txns=15, inject_fan_in=2)
    g1 = _build_graph(accounts1, txns1)
    injected_fan_in = sum(
        1 for a in detect_fan_in(g1, min_distinct_sources=5) if a.kind is AlertKind.FAN_IN
    )
    assert injected_fan_in > baseline_fan_in


def test_injected_fan_out_fires():
    accounts, txns = generate(seed=1, n_accounts=10, n_normal_txns=5, inject_fan_out=1)
    g = _build_graph(accounts, txns)
    alerts = detect_fan_out(g)
    assert any(a.kind is AlertKind.FAN_OUT for a in alerts)


def test_injected_fan_in_fires():
    accounts, txns = generate(seed=1, n_accounts=10, n_normal_txns=5, inject_fan_in=1)
    g = _build_graph(accounts, txns)
    alerts = detect_fan_in(g)
    assert any(a.kind is AlertKind.FAN_IN for a in alerts)


def test_injected_layering_fires():
    accounts, txns = generate(seed=1, n_accounts=5, n_normal_txns=0, inject_layering=1)
    g = _build_graph(accounts, txns)
    alerts = detect_layering_chains(g)
    assert any(a.kind is AlertKind.LAYERING_CHAIN for a in alerts)


def test_injected_round_trip_fires():
    accounts, txns = generate(seed=1, n_accounts=5, n_normal_txns=0, inject_round_trip=1)
    g = _build_graph(accounts, txns)
    alerts = detect_round_trips(g)
    assert any(a.kind is AlertKind.ROUND_TRIP for a in alerts)


def test_injected_structured_fires():
    accounts, txns = generate(seed=1, n_accounts=5, n_normal_txns=0, inject_structured=1)
    g = _build_graph(accounts, txns)
    alerts = detect_structured_deposits(g)
    assert any(a.kind is AlertKind.STRUCTURED_DEPOSIT for a in alerts)


def test_all_five_patterns_together():
    """Inject one of each pattern; every detector should fire."""
    accounts, txns = generate(
        seed=2,
        n_accounts=10,
        n_normal_txns=10,
        inject_fan_out=1,
        inject_fan_in=1,
        inject_layering=1,
        inject_round_trip=1,
        inject_structured=1,
    )
    g = _build_graph(accounts, txns)
    kinds = {
        a.kind
        for a in (
            detect_fan_out(g)
            + detect_fan_in(g)
            + detect_layering_chains(g)
            + detect_round_trips(g)
            + detect_structured_deposits(g)
        )
    }
    assert kinds == {
        AlertKind.FAN_OUT,
        AlertKind.FAN_IN,
        AlertKind.LAYERING_CHAIN,
        AlertKind.ROUND_TRIP,
        AlertKind.STRUCTURED_DEPOSIT,
    }


def test_simulator_sorts_by_time():
    accounts, txns = generate(seed=3, inject_layering=1)
    assert all(txns[i].occurred_at <= txns[i + 1].occurred_at for i in range(len(txns) - 1))
