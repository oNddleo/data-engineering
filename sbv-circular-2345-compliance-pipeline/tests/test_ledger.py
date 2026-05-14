"""Ledger + hash-chain tests."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from sbv2345.ledger import AuditLedger, SealedAuditRecord, TamperDetected
from sbv2345.schema import VN_TZ, AuthMethod

from ._fixtures import make_audit_event, make_txn

_NOW = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)


def test_genesis_tip_hash_is_zeros():
    ledger = AuditLedger()
    assert ledger.tip_hash == "0" * 64
    assert ledger.length == 0


def test_append_one_event():
    ledger = AuditLedger()
    rec = ledger.append(make_audit_event(), sealed_at=_NOW)
    assert ledger.length == 1
    assert rec.sequence_number == 1
    assert rec.prev_hash == "0" * 64
    assert len(rec.record_hash) == 64


def test_append_chains_subsequent_records():
    ledger = AuditLedger()
    a = ledger.append(make_audit_event(txn=make_txn(txn_id="A", amount=15_000_000)), sealed_at=_NOW)
    b = ledger.append(make_audit_event(txn=make_txn(txn_id="B", amount=20_000_000)), sealed_at=_NOW)
    assert b.sequence_number == 2
    assert b.prev_hash == a.record_hash


def test_verify_passes_on_clean_chain():
    ledger = AuditLedger()
    for i in range(5):
        ledger.append(
            make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)),
            sealed_at=_NOW,
        )
    ledger.verify()  # no raise


def test_verify_detects_in_place_tamper():
    ledger = AuditLedger()
    for i in range(3):
        ledger.append(
            make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)),
            sealed_at=_NOW,
        )
    # Mutate a record's event indirectly — replace it in the internal list.
    bad_event = make_audit_event(txn=make_txn(txn_id="T-1", amount=99_999_999))
    bad_rec = dataclasses.replace(ledger._records[1], event=bad_event)
    ledger._records[1] = bad_rec
    with pytest.raises(TamperDetected) as e:
        ledger.verify()
    assert e.value.sequence_number == 2


def test_verify_detects_swapped_record_hash():
    ledger = AuditLedger()
    for i in range(3):
        ledger.append(
            make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)),
            sealed_at=_NOW,
        )
    bad = dataclasses.replace(ledger._records[1], record_hash="0" * 64)
    ledger._records[1] = bad
    with pytest.raises(TamperDetected):
        ledger.verify()


def test_verify_detects_renumbered_sequence():
    ledger = AuditLedger()
    for i in range(2):
        ledger.append(
            make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)),
            sealed_at=_NOW,
        )
    bad = dataclasses.replace(ledger._records[1], sequence_number=99)
    ledger._records[1] = bad
    with pytest.raises(TamperDetected):
        ledger.verify()


def test_append_rejects_naive_sealed_at():
    ledger = AuditLedger()
    with pytest.raises(ValueError):
        ledger.append(make_audit_event(), sealed_at=datetime(2026, 5, 14, 9, 0))


def test_query_filters_by_account():
    ledger = AuditLedger()
    ledger.append(
        make_audit_event(txn=make_txn(initiator="ACC-A", amount=15_000_000, txn_id="A")),
        sealed_at=_NOW,
    )
    ledger.append(
        make_audit_event(txn=make_txn(initiator="ACC-B", amount=15_000_000, txn_id="B")),
        sealed_at=_NOW,
    )
    only_a = ledger.query(account="ACC-A")
    assert len(only_a) == 1
    assert only_a[0].event.txn.initiator_account == "ACC-A"


def test_query_filters_by_time_window():
    ledger = AuditLedger()
    for i in range(3):
        ledger.append(
            make_audit_event(
                txn=make_txn(
                    amount=15_000_000, occurred_at=datetime(2026, 5, 14 + i, 9, 0, tzinfo=VN_TZ)
                ),
            ),
            sealed_at=_NOW,
        )
    out = ledger.query(
        since=datetime(2026, 5, 14, 12, 0, tzinfo=VN_TZ),
        until=datetime(2026, 5, 15, 12, 0, tzinfo=VN_TZ),
    )
    assert len(out) == 1


def test_query_filters_by_trigger_kind():
    from sbv2345.schema import TriggerKind

    ledger = AuditLedger()
    ledger.append(make_audit_event(triggers=(TriggerKind.SINGLE_TXN_OVER_10M,)), sealed_at=_NOW)
    ledger.append(make_audit_event(triggers=(TriggerKind.INTERNATIONAL_TRANSFER,)), sealed_at=_NOW)
    only_xb = ledger.query(triggered_kind="INTERNATIONAL_TRANSFER")
    assert len(only_xb) == 1


def test_seal_day_with_no_records_uses_empty_root():
    from sbv2345.merkle import EMPTY_ROOT

    ledger = AuditLedger()
    seal = ledger.seal_day(_NOW.date(), sealed_at=_NOW)
    assert seal.record_count == 0
    assert seal.merkle_root == EMPTY_ROOT


def test_seal_day_with_records_yields_64_hex_root():
    ledger = AuditLedger()
    for i in range(4):
        ledger.append(
            make_audit_event(txn=make_txn(amount=15_000_000, occurred_at=_NOW, txn_id=f"T-{i}")),
            sealed_at=_NOW,
        )
    seal = ledger.seal_day(_NOW.date(), sealed_at=_NOW)
    assert seal.record_count == 4
    assert len(seal.merkle_root) == 64


def test_seal_day_groups_by_occurred_at_date():
    """Records from other calendar days don't influence the seal."""
    ledger = AuditLedger()
    ledger.append(
        make_audit_event(
            txn=make_txn(amount=15_000_000, occurred_at=datetime(2026, 5, 13, 9, 0, tzinfo=VN_TZ))
        ),
        sealed_at=_NOW,
    )
    ledger.append(
        make_audit_event(
            txn=make_txn(amount=15_000_000, occurred_at=datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ))
        ),
        sealed_at=_NOW,
    )
    seal = ledger.seal_day(_NOW.date(), sealed_at=_NOW)
    assert seal.record_count == 1


def test_records_returns_copy():
    ledger = AuditLedger()
    ledger.append(make_audit_event(), sealed_at=_NOW)
    recs = ledger.records()
    recs.clear()
    assert ledger.length == 1  # internal list unchanged


def test_append_many():
    ledger = AuditLedger()
    out = ledger.append_many(
        [make_audit_event(txn=make_txn(txn_id=f"T-{i}", amount=15_000_000 + i)) for i in range(3)],
        sealed_at=_NOW,
    )
    assert len(out) == 3
    assert ledger.length == 3


def test_record_hash_changes_with_auth_method():
    """Hash is sensitive to the txn's auth_method field."""
    from sbv2345.schema import BiometricMethod

    ledger_a = AuditLedger()
    ledger_b = AuditLedger()
    pin_event = make_audit_event(txn=make_txn(auth_method=AuthMethod.PIN, amount=15_000_000))
    bio_event = make_audit_event(
        txn=make_txn(
            auth_method=AuthMethod.BIOMETRIC,
            biometric_method=BiometricMethod.FACE,
            amount=15_000_000,
        )
    )
    a = ledger_a.append(pin_event, sealed_at=_NOW)
    b = ledger_b.append(bio_event, sealed_at=_NOW)
    assert a.record_hash != b.record_hash


def test_isinstance_sealed_record():
    ledger = AuditLedger()
    rec = ledger.append(make_audit_event(), sealed_at=_NOW)
    assert isinstance(rec, SealedAuditRecord)
