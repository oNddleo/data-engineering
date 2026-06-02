"""Scoring tests."""

from __future__ import annotations

import pytest

from amlgraph.alerts import AlertKind, AMLAlert, Severity
from amlgraph.graph import TransactionGraph
from amlgraph.schema import RiskFlag
from amlgraph.scoring import KIND_MULTIPLIER, SEVERITY_POINTS, score_accounts, top_n

from ._fixtures import make_account, make_txn


def test_empty_graph_no_alerts_returns_empty():
    g = TransactionGraph()
    scores = score_accounts(g, [])
    assert scores == {}


def test_apriori_risk_flags_contribute():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A", risk_flags=(RiskFlag.SANCTIONED,)))
    scores = score_accounts(g, [])
    assert scores["A"] == 100  # SANCTIONED = 100


def test_pep_and_mule_stack():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A", risk_flags=(RiskFlag.PEP, RiskFlag.MULE_SUSPECTED)))
    scores = score_accounts(g, [])
    assert scores["A"] == 30 + 50  # PEP + MULE_SUSPECTED


def test_alert_contributes_severity_times_multiplier_to_primary():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A"))
    a = AMLAlert(
        kind=AlertKind.FAN_OUT,
        severity=Severity.WARN,
        primary_account="A",
        related_accounts=("B",),
        total_amount_vnd=0,
    )
    scores = score_accounts(g, [a])
    expected = int(SEVERITY_POINTS[Severity.WARN] * KIND_MULTIPLIER[AlertKind.FAN_OUT])
    assert scores["A"] == expected


def test_related_accounts_get_half_credit():
    g = TransactionGraph()
    a = AMLAlert(
        kind=AlertKind.FAN_OUT,
        severity=Severity.WARN,
        primary_account="A",
        related_accounts=("B",),
        total_amount_vnd=0,
    )
    scores = score_accounts(g, [a])
    primary = int(SEVERITY_POINTS[Severity.WARN] * KIND_MULTIPLIER[AlertKind.FAN_OUT])
    assert scores["B"] == primary // 2


def test_crit_alert_outweighs_warn():
    g = TransactionGraph()
    warn = AMLAlert(
        kind=AlertKind.FAN_OUT,
        severity=Severity.WARN,
        primary_account="W",
        related_accounts=(),
        total_amount_vnd=0,
    )
    crit = AMLAlert(
        kind=AlertKind.ROUND_TRIP,
        severity=Severity.CRIT,
        primary_account="C",
        related_accounts=(),
        total_amount_vnd=0,
    )
    scores = score_accounts(g, [warn, crit])
    assert scores["C"] > scores["W"]


def test_top_n_sorts_descending():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A", risk_flags=(RiskFlag.SANCTIONED,)))
    g.add_account(make_account(account_id="B", risk_flags=(RiskFlag.PEP,)))
    g.add_account(make_account(account_id="C"))
    ranked = top_n(score_accounts(g, []), n=10)
    assert [r.account_id for r in ranked] == ["A", "B"]  # C has 0 score, excluded


def test_top_n_rejects_zero():
    with pytest.raises(ValueError):
        top_n({}, n=0)


def test_alerts_accumulate_per_account():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A"))
    a1 = AMLAlert(
        kind=AlertKind.FAN_OUT,
        severity=Severity.WARN,
        primary_account="A",
        related_accounts=(),
        total_amount_vnd=0,
    )
    a2 = AMLAlert(
        kind=AlertKind.FAN_IN,
        severity=Severity.WARN,
        primary_account="A",
        related_accounts=(),
        total_amount_vnd=0,
    )
    scores = score_accounts(g, [a1, a2])
    expected = int(SEVERITY_POINTS[Severity.WARN] * KIND_MULTIPLIER[AlertKind.FAN_OUT]) + int(
        SEVERITY_POINTS[Severity.WARN] * KIND_MULTIPLIER[AlertKind.FAN_IN]
    )
    assert scores["A"] == expected


def test_graph_implied_accounts_in_scores_table():
    """Even accounts only mentioned via edges get a score entry (0 if no flags/alerts)."""
    g = TransactionGraph()
    g.add_transaction(make_txn(src="X", dst="Y"))
    scores = score_accounts(g, [])
    assert "X" in scores
    assert "Y" in scores
    assert scores["X"] == 0


def test_top_n_truncates():
    g = TransactionGraph()
    for i in range(5):
        g.add_account(make_account(account_id=f"A{i}", risk_flags=(RiskFlag.PEP,)))
    ranked = top_n(score_accounts(g, []), n=3)
    assert len(ranked) == 3
