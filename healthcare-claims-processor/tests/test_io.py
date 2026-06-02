"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from bhyt.io_jsonl import (
    card_from_dict,
    claim_from_dict,
    dump_cards,
    dump_claims,
    dump_patients,
    dump_reimbursements,
    load_cards,
    load_claims,
    load_patients,
    load_reimbursements,
    patient_from_dict,
    reimb_from_dict,
)
from bhyt.schema import Reimbursement

from ._fixtures import make_card, make_claim, make_patient


def test_patient_roundtrip():
    p = make_patient()
    [back] = load_patients(dump_patients([p]))
    assert back == p


def test_card_roundtrip():
    c = make_card()
    [back] = load_cards(dump_cards([c]))
    assert back == c


def test_claim_roundtrip():
    c = make_claim()
    [back] = load_claims(dump_claims([c]))
    assert back == c


def test_reimbursement_roundtrip():
    r = Reimbursement(
        claim_id="CL-001",
        subtotal_vnd=500_000,
        coverage_rate_bps=8_000,
        referral_penalty_bps=10_000,
        insurer_pays_vnd=400_000,
        patient_pays_vnd=100_000,
        notes=("test note",),
    )
    [back] = load_reimbursements(dump_reimbursements([r]))
    assert back == r


def test_patient_decoder_rejects_bool_for_str():
    bad = {
        "patient_id": True,
        "full_name": "x",
        "date_of_birth": "2000-01-01",
        "sex": "M",
        "province_code": "01",
    }
    with pytest.raises(TypeError):
        patient_from_dict(bad)


def test_card_decoder_rejects_unknown_category():
    bad = {
        "card_number": "D40179012345678",
        "category": "WEIRD_CATEGORY",
        "valid_from": "2024-01-01",
        "valid_to": "2027-01-01",
    }
    with pytest.raises(ValueError):
        card_from_dict(bad)


def test_claim_decoder_rejects_non_list_items():
    bad = {
        "claim_id": "x",
        "patient_id": "p",
        "card_number": "D40179012345678",
        "care_level": "HUYEN",
        "service_kind": "OUTPATIENT",
        "has_referral": True,
        "same_province": True,
        "visited_at": "2026-05-17T09:00:00+07:00",
        "diagnoses": [],
        "items": "not a list",
        "subtotal_vnd": 0,
    }
    with pytest.raises(TypeError):
        claim_from_dict(bad)


def test_reimb_decoder_rejects_bool_for_int():
    bad = {
        "claim_id": "x",
        "subtotal_vnd": True,
        "coverage_rate_bps": 8_000,
        "referral_penalty_bps": 10_000,
        "insurer_pays_vnd": 0,
        "patient_pays_vnd": 0,
        "notes": [],
    }
    with pytest.raises(TypeError, match="subtotal_vnd"):
        reimb_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_patients([make_patient()])
    padded = "\n\n" + text + "\n\n"
    assert len(load_patients(padded)) == 1


def test_multi_claim_roundtrip():
    claims = [make_claim(claim_id=f"CL-{i:03d}") for i in range(5)]
    text = dump_claims(claims)
    assert load_claims(text) == claims
