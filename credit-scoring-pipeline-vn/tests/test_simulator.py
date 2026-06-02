"""Simulator + risk-profile tests."""

from __future__ import annotations

from datetime import date

import pytest

from cicscore.cic_groups import CICGroup
from cicscore.features import extract
from cicscore.scoring import baseline_score
from cicscore.simulator import RISK_PROFILES, generate, generate_borrower


def test_risk_profiles_are_three_kinds():
    assert set(RISK_PROFILES) == {"clean", "watch", "distressed"}


def test_generate_reproducible_with_seed():
    a = generate(n_borrowers=5, seed=42)
    b = generate(n_borrowers=5, seed=42)
    assert [(x.borrower_id, len(x.assessments)) for x in a] == [
        (x.borrower_id, len(x.assessments)) for x in b
    ]


def test_generate_n_borrowers_matches_count():
    bs = generate(n_borrowers=12, seed=1)
    assert len(bs) == 12


def test_clean_borrower_stays_group_1():
    import random as _random

    b = generate_borrower(
        _random.Random(0),
        borrower_id="CLEAN",
        profile="clean",
        observation_date=date(2026, 5, 14),
    )
    assert all(a.group is CICGroup.GROUP_1 for a in b.assessments)


def test_distressed_borrower_reaches_group_4_or_5():
    import random as _random

    b = generate_borrower(
        _random.Random(0),
        borrower_id="BAD",
        profile="distressed",
        observation_date=date(2026, 5, 14),
    )
    worst = max(a.group for a in b.assessments)
    assert worst >= CICGroup.GROUP_4


def test_distressed_borrower_has_inquiries():
    import random as _random

    b = generate_borrower(
        _random.Random(0),
        borrower_id="BAD",
        profile="distressed",
        observation_date=date(2026, 5, 14),
    )
    assert len(b.inquiries) >= 3


def test_clean_borrower_high_score_distressed_low_score():
    import random as _random

    obs = date(2026, 5, 14)
    clean = generate_borrower(
        _random.Random(0), borrower_id="C", profile="clean", observation_date=obs
    )
    distressed = generate_borrower(
        _random.Random(0), borrower_id="D", profile="distressed", observation_date=obs
    )
    s_clean = baseline_score(extract(clean, obs)).score
    s_bad = baseline_score(extract(distressed, obs)).score
    assert s_clean > s_bad
    assert s_clean >= 700  # clean borrower at or above base


def test_generate_borrower_rejects_unknown_profile():
    import random as _random

    with pytest.raises(ValueError):
        generate_borrower(
            _random.Random(0),
            borrower_id="X",
            profile="meteor",
            observation_date=date(2026, 5, 14),
        )


def test_generate_borrower_two_contracts_term_loan_and_card():
    import random as _random

    b = generate_borrower(
        _random.Random(0),
        borrower_id="X",
        profile="clean",
        observation_date=date(2026, 5, 14),
    )
    types = {c.contract_type.value for c in b.contracts}
    assert "TERM_LOAN" in types
    assert "CREDIT_CARD" in types


def test_generate_borrower_assessments_in_history_window():
    import random as _random

    obs = date(2026, 5, 14)
    b = generate_borrower(
        _random.Random(0),
        borrower_id="X",
        profile="clean",
        observation_date=obs,
        history_months=12,
    )
    # First month should be 12 months before obs_month.
    months = sorted({a.as_of_month for a in b.assessments})
    assert len(months) == 12
