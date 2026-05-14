"""Hypothesis property tests."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from sbv2345.io_jsonl import dump_ledger, dump_txns, load_ledger, load_txns
from sbv2345.ledger import AuditLedger
from sbv2345.merkle import merkle_root
from sbv2345.schema import VN_TZ

from ._fixtures import make_audit_event, make_txn


def _h(seed: int) -> str:
    return hashlib.sha256(str(seed).encode()).hexdigest()


_NOW = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)


@given(amount=st.integers(min_value=1, max_value=10**11))
def test_txn_round_trips_through_jsonl(amount):
    """Property: any positive integer VND amount round-trips."""
    t = make_txn(amount=amount)
    out = dump_txns([t])
    loaded = list(load_txns(out))
    assert loaded == [t]


@given(n=st.integers(min_value=0, max_value=30))
def test_ledger_chain_verifies_for_any_length(n):
    """Property: ledger.verify() never raises on a freshly-built clean chain."""
    ledger = AuditLedger()
    for i in range(n):
        ledger.append(
            make_audit_event(
                txn=make_txn(
                    txn_id=f"T-{i}", amount=15_000_000 + i, occurred_at=_NOW + timedelta(seconds=i)
                )
            ),
            sealed_at=_NOW,
        )
    ledger.verify()  # must not raise
    assert ledger.length == n


@given(leaf_count=st.integers(min_value=0, max_value=20))
def test_merkle_root_deterministic(leaf_count):
    leaves = [_h(i) for i in range(leaf_count)]
    assert merkle_root(leaves) == merkle_root(leaves)


@given(leaf_count=st.integers(min_value=1, max_value=20))
def test_merkle_root_is_64_hex_for_nonempty(leaf_count):
    leaves = [_h(i) for i in range(leaf_count)]
    root = merkle_root(leaves)
    assert len(root) == 64
    int(root, 16)  # parses as hex


@given(n=st.integers(min_value=0, max_value=15))
def test_dump_load_ledger_round_trip(n):
    ledger = AuditLedger()
    for i in range(n):
        ledger.append(
            make_audit_event(
                txn=make_txn(
                    txn_id=f"T-{i}", amount=15_000_000 + i, occurred_at=_NOW + timedelta(seconds=i)
                )
            ),
            sealed_at=_NOW,
        )
    rehydrated = load_ledger(dump_ledger(ledger))
    assert rehydrated.length == n
    assert rehydrated.tip_hash == ledger.tip_hash
