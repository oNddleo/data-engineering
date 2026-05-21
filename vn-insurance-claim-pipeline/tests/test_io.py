"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import date

import pytest

from vnbhyt.io_jsonl import (
    claim_from_dict,
    claim_to_dict,
    dump_claims,
    dump_payouts,
    load_claims,
    load_payouts,
)
from vnbhyt.payout import compute
from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier


def _sample() -> Claim:
    return Claim(
        claim_id="C-001",
        patient_id="P-001",
        card_class=CardClass.EMPLOYEE,
        hospital_tier=HospitalTier.PROVINCIAL,
        care_type=CareType.INPATIENT,
        icd10="J18.9",
        billed_amount_vnd=5_000_000,
        visited_on=date(2026, 3, 15),
        is_in_network=True,
    )


def test_claim_roundtrip() -> None:
    c = _sample()
    assert claim_from_dict(claim_to_dict(c)) == c


def test_claims_dump_load() -> None:
    cs = [_sample()]
    assert load_claims(dump_claims(cs)) == cs


def test_payout_roundtrip() -> None:
    ps = [compute(_sample())]
    assert load_payouts(dump_payouts(ps)) == ps


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_claims("[1,2,3]\n")
