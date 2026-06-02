"""JSONL codec round-trip tests."""

from __future__ import annotations

import json

from n247mon.alerts import Alert, AlertKind, Severity
from n247mon.io_jsonl import (
    alert_from_dict,
    alert_to_dict,
    dump_alerts,
    dump_txns,
    load_alerts,
    load_txns,
    txn_from_dict,
    txn_to_dict,
)

from ._fixtures import make_txn


def test_txn_round_trips():
    t = make_txn(amount=12_345_678, biometric=True)
    d = txn_to_dict(t)
    t2 = txn_from_dict(d)
    assert t2 == t


def test_txn_dict_is_json_serialisable():
    d = txn_to_dict(make_txn())
    assert json.loads(json.dumps(d)) == d


def test_alert_round_trips():
    a = Alert(
        kind=AlertKind.STRUCTURING_SUSPECTED,
        severity=Severity.WARN,
        txn_id="T-1",
        account="A-1",
        detail="some detail",
        amount_vnd=9_800_000,
    )
    a2 = alert_from_dict(alert_to_dict(a))
    assert a2 == a


def test_dump_load_txns_round_trip():
    txns = [make_txn(txn_id=f"T-{i}", amount=1_000_000 + i) for i in range(5)]
    text = dump_txns(txns)
    loaded = list(load_txns(text))
    assert loaded == txns


def test_dump_load_alerts_round_trip():
    alerts = [
        Alert(
            kind=AlertKind.BLACKLIST_HIT,
            severity=Severity.CRIT,
            txn_id=f"T-{i}",
            account=f"A-{i}",
            detail="x",
            amount_vnd=1_000,
        )
        for i in range(3)
    ]
    loaded = list(load_alerts(dump_alerts(alerts)))
    assert loaded == alerts


def test_load_txns_skips_blank_lines():
    line = json.dumps(txn_to_dict(make_txn()))
    text = "\n\n" + line + "\n\n" + line + "\n"
    loaded = list(load_txns(text))
    assert len(loaded) == 2


def test_dump_txns_has_newline_per_record():
    txns = [make_txn(txn_id=f"T-{i}") for i in range(3)]
    out = dump_txns(txns)
    assert out.count("\n") == 3  # one per record


def test_dump_empty_iterables():
    assert dump_txns([]) == "\n"  # just trailing newline
    assert list(load_txns("")) == []
    assert list(load_alerts("\n  \n")) == []
