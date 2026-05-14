"""JSONL codec tests."""

from __future__ import annotations

import json
from datetime import date

from cicscore.cic_groups import CICGroup
from cicscore.io_jsonl import (
    assessment_from_dict,
    assessment_to_dict,
    borrower_from_dict,
    borrower_to_dict,
    contract_from_dict,
    contract_to_dict,
    dump_borrowers,
    dump_features,
    dump_scores,
    inquiry_from_dict,
    inquiry_to_dict,
    load_borrowers,
)
from cicscore.simulator import generate_borrower

from ._fixtures import (
    make_assessment,
    make_borrower,
    make_contract,
    make_inquiry,
)


def test_contract_round_trips():
    c = make_contract(closed_at=date(2025, 6, 1))
    assert contract_from_dict(contract_to_dict(c)) == c


def test_contract_with_none_closed_at_round_trips():
    c = make_contract(closed_at=None)
    assert contract_from_dict(contract_to_dict(c)) == c


def test_assessment_round_trips():
    a = make_assessment(as_of_month=date(2026, 5, 1), group=CICGroup.GROUP_3, days_past_due=100)
    assert assessment_from_dict(assessment_to_dict(a)) == a


def test_inquiry_round_trips():
    q = make_inquiry(inquired_at=date(2026, 5, 1), purpose="CARD_APPLICATION")
    assert inquiry_from_dict(inquiry_to_dict(q)) == q


def test_borrower_round_trip_dict():
    import random as _random

    b = generate_borrower(
        _random.Random(0),
        borrower_id="X-1",
        profile="watch",
        observation_date=date(2026, 5, 14),
    )
    b2 = borrower_from_dict(borrower_to_dict(b))
    assert b2.borrower_id == b.borrower_id
    assert len(b2.contracts) == len(b.contracts)
    assert len(b2.assessments) == len(b.assessments)
    assert len(b2.inquiries) == len(b.inquiries)
    assert b2.monthly_income_vnd == b.monthly_income_vnd


def test_dump_load_borrowers_jsonl_round_trip():
    bs = [make_borrower(borrower_id=f"B-{i}") for i in range(3)]
    text = dump_borrowers(bs)
    loaded = list(load_borrowers(text))
    assert [b.borrower_id for b in loaded] == [b.borrower_id for b in bs]


def test_borrower_dict_is_json_serialisable():
    b = make_borrower()
    assert json.loads(json.dumps(borrower_to_dict(b))) == borrower_to_dict(b)


def test_dump_features_and_scores_compile():
    """Just ensure the codec round-trips a typical output without exploding."""
    import random as _random

    from cicscore.features import extract
    from cicscore.scoring import baseline_score

    b = generate_borrower(
        _random.Random(0),
        borrower_id="X",
        profile="clean",
        observation_date=date(2026, 5, 14),
    )
    f = extract(b, date(2026, 5, 14))
    s = baseline_score(f)
    txt_f = dump_features([f])
    txt_s = dump_scores([s])
    assert "borrower_id" in txt_f
    assert "score" in txt_s
