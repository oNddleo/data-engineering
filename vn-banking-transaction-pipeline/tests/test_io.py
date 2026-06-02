"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vnbank.aml import find_ctr
from vnbank.io_jsonl import (
    aml_from_dict,
    aml_to_dict,
    dump_amls,
    dump_summaries,
    dump_txns,
    load_amls,
    load_summaries,
    load_txns,
    txn_from_dict,
    txn_to_dict,
)
from vnbank.schema import CTR_THRESHOLD_VND, TxnDirection, TxnKind
from vnbank.summary import aggregate_daily

from ._fixtures import make_txn


def test_txn_roundtrip_basic() -> None:
    t = make_txn()
    assert txn_from_dict(txn_to_dict(t)) == t


def test_txn_roundtrip_with_counterparty() -> None:
    t = make_txn(
        kind=TxnKind.INTERBANK_TRANSFER,
        counterparty_account="9999999999",
        counterparty_bank_bin="970418",
        description="Hoa don 001",
    )
    assert txn_from_dict(txn_to_dict(t)) == t


def test_txn_dump_load_multiple() -> None:
    txns = [make_txn(txn_id=f"T-{i}") for i in range(5)]
    out = load_txns(dump_txns(txns))
    assert out == txns


def test_txn_dump_skips_blank_lines() -> None:
    txns = [make_txn()]
    text = dump_txns(txns) + "\n\n   \n"
    assert load_txns(text) == txns


def test_summary_roundtrip() -> None:
    txns = [make_txn(txn_id=f"T-{i}") for i in range(3)]
    summaries = aggregate_daily(txns)
    out = load_summaries(dump_summaries(summaries))
    assert out == summaries


def test_aml_roundtrip() -> None:
    t = make_txn(
        kind=TxnKind.CASH_DEPOSIT,
        direction=TxnDirection.CREDIT,
        amount_vnd=CTR_THRESHOLD_VND,
    )
    findings = find_ctr([t])
    out = load_amls(dump_amls(findings))
    assert out == findings


def test_aml_dict_direct() -> None:
    from vnbank.aml import AMLFinding, AMLKind

    f = AMLFinding(
        kind=AMLKind.STRUCTURING,
        account_number="123",
        bank_bin="970436",
        detail="test",
        metric=42,
    )
    assert aml_from_dict(aml_to_dict(f)) == f


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_txns("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    bad = '{"txn_id": 1, "account_number": "x"}\n'
    with pytest.raises(TypeError):
        load_txns(bad)
