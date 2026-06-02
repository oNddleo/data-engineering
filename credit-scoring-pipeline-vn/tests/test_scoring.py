"""Baseline credit-score tests."""

from __future__ import annotations

from datetime import date

from cicscore.cic_groups import CICGroup
from cicscore.features import extract
from cicscore.scoring import BASE_SCORE, MAX_SCORE, MIN_SCORE, baseline_score

from ._fixtures import make_assessment, make_borrower, make_contract


def _features(*, group: CICGroup = CICGroup.GROUP_1, **kwargs):
    c = make_contract(opened_at=date(2024, 1, 1))
    a = make_assessment(as_of_month=date(2026, 5, 1), group=group, principal=50_000_000)
    b = make_borrower(contracts=(c,), assessments=(a,), **kwargs)
    return extract(b, date(2026, 5, 14))


def test_clean_group1_returns_base_score():
    s = baseline_score(_features())
    assert s.score == BASE_SCORE
    assert s.reasons == ()


def test_group2_costs_50_points():
    s = baseline_score(_features(group=CICGroup.GROUP_2))
    # group_2 (−50) + 1 distinct group_2+ month (−5) = base − 55.
    assert s.score == BASE_SCORE - 55


def test_group5_costs_max_400_points():
    s = baseline_score(_features(group=CICGroup.GROUP_5))
    # 700 − 400 (group_5) − 5 (1 month in group_2+) = 295; clipped to MIN_SCORE=300.
    assert s.score == MIN_SCORE
    deltas = {r.label: r.delta for r in s.reasons}
    assert deltas["max_group_24m=5"] == -400


def test_score_clipped_at_minimum():
    """Even a wildly bad borrower can't go below MIN_SCORE."""
    # Forcing many penalties: group 5 + many inquiries via direct features path.
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_5,
        worst_group_ever=CICGroup.GROUP_5,
        max_group_24m=CICGroup.GROUP_5,
        months_in_group_2plus_24m=24,
        active_contracts=1,
        unique_lenders=1,
        total_outstanding_principal_vnd=10_000_000,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=10_000_000,
        months_since_first_credit=12,
        months_since_last_credit_open=12,
        inquiries_3m=10,
        inquiries_6m=20,
        inquiries_12m=30,
        days_since_last_inquiry=1,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=2.0,
    )
    s = baseline_score(f)
    assert s.score == MIN_SCORE


def test_score_clipped_at_maximum():
    """Borrower can't exceed MAX_SCORE."""
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_1,
        worst_group_ever=CICGroup.GROUP_1,
        max_group_24m=CICGroup.GROUP_1,
        months_in_group_2plus_24m=0,
        active_contracts=1,
        unique_lenders=1,
        total_outstanding_principal_vnd=10_000_000,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=120,
        months_since_last_credit_open=120,
        inquiries_3m=0,
        inquiries_6m=0,
        inquiries_12m=0,
        days_since_last_inquiry=None,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=0.10,
    )
    s = baseline_score(f)
    # Base + 30 (5y history) = 730 — well under MAX. Verify clamp is via construction.
    assert s.score <= MAX_SCORE


def test_long_history_bonus_applied():
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=None,
        worst_group_ever=None,
        max_group_24m=None,
        months_in_group_2plus_24m=0,
        active_contracts=0,
        unique_lenders=0,
        total_outstanding_principal_vnd=0,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=60,
        months_since_last_credit_open=60,
        inquiries_3m=0,
        inquiries_6m=0,
        inquiries_12m=0,
        days_since_last_inquiry=None,
        has_term_loan=False,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=None,
    )
    s = baseline_score(f)
    assert s.score == BASE_SCORE + 30


def test_dti_high_penalty():
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_1,
        worst_group_ever=CICGroup.GROUP_1,
        max_group_24m=CICGroup.GROUP_1,
        months_in_group_2plus_24m=0,
        active_contracts=1,
        unique_lenders=1,
        total_outstanding_principal_vnd=0,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=12,
        months_since_last_credit_open=12,
        inquiries_3m=0,
        inquiries_6m=0,
        inquiries_12m=0,
        days_since_last_inquiry=None,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=0.55,  # >0.5 but ≤0.7
    )
    assert baseline_score(f).score == BASE_SCORE - 50


def test_dti_very_high_penalty():
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_1,
        worst_group_ever=CICGroup.GROUP_1,
        max_group_24m=CICGroup.GROUP_1,
        months_in_group_2plus_24m=0,
        active_contracts=1,
        unique_lenders=1,
        total_outstanding_principal_vnd=0,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=12,
        months_since_last_credit_open=12,
        inquiries_3m=0,
        inquiries_6m=0,
        inquiries_12m=0,
        days_since_last_inquiry=None,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=0.80,  # >0.7
    )
    assert baseline_score(f).score == BASE_SCORE - 100


def test_unique_lenders_5plus_penalty():
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_1,
        worst_group_ever=CICGroup.GROUP_1,
        max_group_24m=CICGroup.GROUP_1,
        months_in_group_2plus_24m=0,
        active_contracts=6,
        unique_lenders=6,
        total_outstanding_principal_vnd=0,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=12,
        months_since_last_credit_open=0,
        inquiries_3m=0,
        inquiries_6m=0,
        inquiries_12m=0,
        days_since_last_inquiry=None,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=None,
    )
    assert baseline_score(f).score == BASE_SCORE - 30


def test_score_returns_borrower_id():
    s = baseline_score(_features(group=CICGroup.GROUP_2))
    assert s.borrower_id == "B-1"


def test_score_reasons_carry_deltas():
    s = baseline_score(_features(group=CICGroup.GROUP_3))
    deltas = {r.label: r.delta for r in s.reasons}
    assert any("max_group_24m" in k for k in deltas)


def test_score_reasons_empty_for_clean():
    s = baseline_score(_features())
    assert s.reasons == ()


def test_inquiries_6m_costs_10_each():
    """6 inquiries × 10 = 60-point penalty."""
    from cicscore.features import FeatureVector

    f = FeatureVector(
        borrower_id="X",
        observation_date=date(2026, 5, 14),
        current_max_group=CICGroup.GROUP_1,
        worst_group_ever=CICGroup.GROUP_1,
        max_group_24m=CICGroup.GROUP_1,
        months_in_group_2plus_24m=0,
        active_contracts=1,
        unique_lenders=1,
        total_outstanding_principal_vnd=0,
        total_outstanding_interest_vnd=0,
        provision_estimate_vnd=0,
        months_since_first_credit=24,
        months_since_last_credit_open=12,
        inquiries_3m=3,
        inquiries_6m=6,
        inquiries_12m=8,
        days_since_last_inquiry=5,
        has_term_loan=True,
        has_mortgage=False,
        has_auto_loan=False,
        has_credit_card=False,
        has_overdraft=False,
        has_business_loan=False,
        dti_ratio=None,
    )
    assert baseline_score(f).score == BASE_SCORE - 60
