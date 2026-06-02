"""JSONL codec tests."""

from __future__ import annotations

from amlgraph.alerts import AlertKind, AMLAlert, Severity
from amlgraph.io_jsonl import (
    account_from_dict,
    account_to_dict,
    alert_from_dict,
    alert_to_dict,
    dump_accounts,
    dump_alerts,
    dump_txns,
    load_accounts,
    load_alerts,
    load_txns,
    txn_from_dict,
    txn_to_dict,
)
from amlgraph.schema import RiskFlag

from ._fixtures import make_account, make_txn


def test_account_round_trip():
    a = make_account(risk_flags=(RiskFlag.PEP, RiskFlag.SANCTIONED))
    assert account_from_dict(account_to_dict(a)) == a


def test_txn_round_trip():
    t = make_txn(amount=5_000_000)
    assert txn_from_dict(txn_to_dict(t)) == t


def test_alert_round_trip():
    a = AMLAlert(
        kind=AlertKind.LAYERING_CHAIN,
        severity=Severity.CRIT,
        primary_account="A",
        related_accounts=("B", "C"),
        total_amount_vnd=1_000_000,
        detail="some detail",
        txn_ids=("T1", "T2"),
    )
    assert alert_from_dict(alert_to_dict(a)) == a


def test_dump_load_accounts():
    accounts = [make_account(account_id=f"A-{i}") for i in range(3)]
    loaded = list(load_accounts(dump_accounts(accounts)))
    assert loaded == accounts


def test_dump_load_txns():
    txns = [make_txn(txn_id=f"T-{i}", amount=1_000 + i) for i in range(5)]
    loaded = list(load_txns(dump_txns(txns)))
    assert loaded == txns


def test_dump_load_alerts():
    alerts = [
        AMLAlert(
            kind=AlertKind.FAN_OUT,
            severity=Severity.WARN,
            primary_account=f"A-{i}",
            related_accounts=(),
            total_amount_vnd=i,
        )
        for i in range(3)
    ]
    loaded = list(load_alerts(dump_alerts(alerts)))
    assert loaded == alerts


def test_load_skips_blank_lines():
    text = "\n\n" + dump_accounts([make_account()])
    assert len(list(load_accounts(text))) == 1
