"""Report tests."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from sbv2345.ledger import AuditLedger
from sbv2345.reports import REGULATOR_CSV_COLUMNS, regulator_csv, summarise
from sbv2345.schema import VN_TZ, AuthMethod, BiometricMethod, TriggerKind

from ._fixtures import make_audit_event, make_txn

_NOW = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)


def _ledger_with_mix() -> AuditLedger:
    ledger = AuditLedger()
    ledger.append(
        make_audit_event(
            txn=make_txn(amount=15_000_000, txn_id="A", auth_method=AuthMethod.OTP),
            triggers=(TriggerKind.SINGLE_TXN_OVER_10M,),
        ),
        sealed_at=_NOW,
    )
    ledger.append(
        make_audit_event(
            txn=make_txn(
                amount=25_000_000,
                txn_id="B",
                auth_method=AuthMethod.BIOMETRIC,
                biometric_method=BiometricMethod.FACE,
                cross_border=True,
            ),
            triggers=(TriggerKind.SINGLE_TXN_OVER_10M, TriggerKind.INTERNATIONAL_TRANSFER),
        ),
        sealed_at=_NOW,
    )
    return ledger


def test_regulator_csv_header_matches():
    ledger = _ledger_with_mix()
    text = regulator_csv(ledger.records())
    first = text.splitlines()[0]
    assert first == ",".join(REGULATOR_CSV_COLUMNS)


def test_regulator_csv_row_count_matches():
    ledger = _ledger_with_mix()
    text = regulator_csv(ledger.records())
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 1 + ledger.length


def test_regulator_csv_round_trips_through_dict_reader():
    ledger = _ledger_with_mix()
    text = regulator_csv(ledger.records())
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["txn_id"] == "A"
    assert rows[0]["amount_vnd"] == "15000000"
    assert rows[1]["triggered_kinds"] == "SINGLE_TXN_OVER_10M|INTERNATIONAL_TRANSFER"
    assert rows[1]["biometric_method"] == "FACE"
    assert rows[1]["cross_border"] == "true"


def test_summary_totals():
    s = summarise(_ledger_with_mix().records())
    assert s.total == 2
    assert s.total_value_vnd == 40_000_000
    assert s.biometric_verified_count == 1
    assert s.cross_border_count == 1


def test_summary_by_trigger():
    s = summarise(_ledger_with_mix().records())
    assert s.by_trigger["SINGLE_TXN_OVER_10M"] == 2
    assert s.by_trigger["INTERNATIONAL_TRANSFER"] == 1


def test_summary_by_channel_and_auth():
    s = summarise(_ledger_with_mix().records())
    assert s.by_channel  # populated
    assert s.by_auth_method["OTP"] == 1
    assert s.by_auth_method["BIOMETRIC"] == 1


def test_summary_empty():
    s = summarise([])
    assert s.total == 0
    assert s.total_value_vnd == 0
    assert s.by_trigger == {}
