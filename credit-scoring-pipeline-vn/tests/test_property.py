"""Hypothesis property tests."""

from __future__ import annotations

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from cicscore.cic_groups import CICGroup, group_from_days_past_due, provision_amount_vnd
from cicscore.features import extract
from cicscore.scoring import MAX_SCORE, MIN_SCORE, baseline_score

from ._fixtures import make_assessment, make_borrower, make_contract


@given(days=st.integers(min_value=-10, max_value=10_000))
def test_group_classification_total(days):
    """Property: group_from_days_past_due returns a CICGroup for any int."""
    g = group_from_days_past_due(days)
    assert isinstance(g, CICGroup)


@given(principal=st.integers(min_value=0, max_value=10**14))
def test_provision_monotonic_in_group(principal):
    """Property: provision is non-decreasing in group severity (for given principal)."""
    provs = [provision_amount_vnd(g, principal) for g in CICGroup]
    assert provs == sorted(provs)


@given(days=st.integers(min_value=0, max_value=10**4))
def test_score_always_in_range(days):
    """Property: baseline_score is clamped to [300, 900] regardless of inputs."""
    c = make_contract(opened_at=date(2024, 1, 1))
    a = make_assessment(
        as_of_month=date(2026, 5, 1),
        group=group_from_days_past_due(days),
        days_past_due=days,
    )
    b = make_borrower(contracts=(c,), assessments=(a,))
    f = extract(b, date(2026, 5, 14))
    s = baseline_score(f)
    assert MIN_SCORE <= s.score <= MAX_SCORE


@given(amount=st.integers(min_value=0, max_value=10**12))
def test_provision_rate_5_is_full_principal(amount):
    """Property: group 5 provision == 100% of principal (rounded down)."""
    assert provision_amount_vnd(CICGroup.GROUP_5, amount) == amount


@given(amount=st.integers(min_value=0, max_value=10**12))
def test_provision_rate_1_is_zero(amount):
    """Property: group 1 provision == 0 regardless of principal."""
    assert provision_amount_vnd(CICGroup.GROUP_1, amount) == 0
