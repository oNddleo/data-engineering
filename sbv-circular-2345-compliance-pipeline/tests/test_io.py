"""JSONL codec tests."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from sbv2345.io_jsonl import (
    dump_ledger,
    dump_txns,
    load_ledger,
    load_txns,
    record_from_dict,
    record_to_dict,
    txn_from_dict,
    txn_to_dict,
)
from sbv2345.ledger import AuditLedger, TamperDetected
from sbv2345.schema import VN_TZ, AuthMethod, BiometricMethod

from ._fixtures import make_audit_event, make_txn

_NOW = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)


def test_txn_dict_round_trip():
    t = make_txn(
        amount=15_000_000,
        auth_method=AuthMethod.BIOMETRIC,
        biometric_method=BiometricMethod.FACE,
    )
    assert txn_from_dict(txn_to_dict(t)) == t


def test_txn_dict_is_json_safe():
    t = make_txn()
    json.dumps(txn_to_dict(t))  # doesn't raise


def test_dump_load_txns_round_trip():
    txns = [make_txn(txn_id=f"T-{i}", amount=1_000_000 + i) for i in range(5)]
    text = dump_txns(txns)
    loaded = list(load_txns(text))
    assert loaded == txns


def test_record_dict_round_trip():
    ledger = AuditLedger()
    rec = ledger.append(make_audit_event(), sealed_at=_NOW)
    assert record_from_dict(record_to_dict(rec)) == rec


def test_dump_load_ledger_round_trip():
    ledger = AuditLedger()
    for i in range(3):
        ledger.append(
            make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)),
            sealed_at=_NOW,
        )
    text = dump_ledger(ledger)
    rehydrated = load_ledger(text)
    assert rehydrated.length == ledger.length
    assert rehydrated.tip_hash == ledger.tip_hash


def test_load_ledger_detects_on_disk_tamper():
    """If someone edits the persisted file, load_ledger() must raise."""
    ledger = AuditLedger()
    ledger.append(make_audit_event(), sealed_at=_NOW)
    ledger.append(make_audit_event(), sealed_at=_NOW)
    text = dump_ledger(ledger)
    tampered = text.replace("15000000", "99999999")
    with pytest.raises(TamperDetected):
        load_ledger(tampered)


def test_load_ledger_empty_input():
    ledger = load_ledger("")
    assert ledger.length == 0


def test_load_txns_skips_blank_lines():
    line = json.dumps(txn_to_dict(make_txn()))
    text = "\n\n" + line + "\n\n"
    loaded = list(load_txns(text))
    assert len(loaded) == 1
