"""JSONL codec round-trips for CDR / RatedCDR / MonthlyBill / FraudFinding."""

from __future__ import annotations

import pytest

from cdrpipe.billing import aggregate_bills
from cdrpipe.fraud import FraudFinding, FraudKind, find_foreign_roaming
from cdrpipe.io_jsonl import (
    cdr_from_dict,
    cdr_to_dict,
    dump_bills,
    dump_cdrs,
    dump_frauds,
    dump_rated,
    load_bills,
    load_cdrs,
    load_frauds,
    load_rated,
)
from cdrpipe.rating import rate
from cdrpipe.schema import Carrier, CDRKind

from ._fixtures import data_cdr, make_cdr, sms_cdr, voice_cdr


def test_cdr_roundtrip_voice() -> None:
    c = voice_cdr(duration_seconds=120)
    out = cdr_from_dict(cdr_to_dict(c))
    assert out == c


def test_cdr_roundtrip_sms() -> None:
    c = sms_cdr()
    assert cdr_from_dict(cdr_to_dict(c)) == c


def test_cdr_roundtrip_data() -> None:
    c = data_cdr(bytes_used=5 * 1024 * 1024)
    assert cdr_from_dict(cdr_to_dict(c)) == c


def test_cdr_roundtrip_with_flags() -> None:
    c = make_cdr(
        kind=CDRKind.VOICE,
        duration_seconds=60,
        is_roaming=True,
        is_premium=True,
        peer_msisdn="19001234",
    )
    assert cdr_from_dict(cdr_to_dict(c)) == c


def test_cdr_dump_load_multiple() -> None:
    cdrs = [voice_cdr(cdr_id=f"V-{i}") for i in range(5)]
    out = load_cdrs(dump_cdrs(cdrs))
    assert out == cdrs


def test_cdr_dump_skips_blank_lines() -> None:
    cdrs = [voice_cdr()]
    text = dump_cdrs(cdrs) + "\n\n   \n"
    assert load_cdrs(text) == cdrs


def test_rated_roundtrip() -> None:
    r = rate(voice_cdr())
    out = load_rated(dump_rated([r]))
    assert out == [r]


def test_bill_roundtrip() -> None:
    bills = aggregate_bills([rate(voice_cdr())])
    out = load_bills(dump_bills(bills))
    assert out == bills


def test_fraud_roundtrip() -> None:
    c = make_cdr(
        kind=CDRKind.VOICE,
        duration_seconds=15 * 60,
        is_roaming=True,
    )
    findings = find_foreign_roaming([rate(c)])
    out = load_frauds(dump_frauds(findings))
    assert out == findings


def test_fraud_dict_direct() -> None:
    f = FraudFinding(
        kind=FraudKind.PREMIUM_RATE_SPIKE,
        subscriber_msisdn="0961234567",
        carrier=Carrier.VIETTEL,
        detail="x",
        metric=42,
    )
    out = load_frauds(dump_frauds([f]))
    assert out == [f]


def test_cdr_load_rejects_non_object() -> None:
    """A JSONL line that isn't a JSON object should raise."""
    with pytest.raises(TypeError, match="object"):
        load_cdrs("[1, 2, 3]\n")


def test_cdr_load_rejects_wrong_type() -> None:
    """A field with the wrong type raises a clean TypeError."""
    bad = '{"cdr_id": 1, "subscriber_msisdn": "x"}\n'
    with pytest.raises(TypeError, match="cdr_id"):
        load_cdrs(bad)
