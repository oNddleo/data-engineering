"""Feature extraction tests — point-in-time correctness is the priority."""

from __future__ import annotations

from datetime import date

from cicscore.cic_groups import CICGroup
from cicscore.features import extract
from cicscore.schema import ContractType

from ._fixtures import (
    make_assessment,
    make_borrower,
    make_contract,
    make_inquiry,
)

# ------ baseline / empty cases --------------------------------------------


def test_extract_empty_borrower():
    b = make_borrower()
    f = extract(b, date(2026, 5, 14))
    assert f.active_contracts == 0
    assert f.unique_lenders == 0
    assert f.current_max_group is None
    assert f.worst_group_ever is None
    assert f.max_group_24m is None
    assert f.months_in_group_2plus_24m == 0
    assert f.total_outstanding_principal_vnd == 0
    assert f.provision_estimate_vnd == 0
    assert f.dti_ratio is None
    assert f.inquiries_3m == 0


def test_extract_group1_clean_borrower():
    c = make_contract(opened_at=date(2024, 1, 1))
    a = make_assessment(
        contract_id="C-1",
        as_of_month=date(2026, 5, 1),
        group=CICGroup.GROUP_1,
        principal=50_000_000,
    )
    b = make_borrower(contracts=(c,), assessments=(a,))
    f = extract(b, date(2026, 5, 14))
    assert f.current_max_group is CICGroup.GROUP_1
    assert f.worst_group_ever is CICGroup.GROUP_1
    assert f.max_group_24m is CICGroup.GROUP_1
    assert f.months_in_group_2plus_24m == 0
    assert f.provision_estimate_vnd == 0


# ------ Point-in-time correctness -----------------------------------------


def test_extract_filters_future_assessments():
    """Assessments dated *after* observation_date must be ignored."""
    c = make_contract(opened_at=date(2024, 1, 1))
    a_past = make_assessment(as_of_month=date(2026, 1, 1), group=CICGroup.GROUP_1)
    a_future = make_assessment(
        as_of_month=date(2026, 10, 1), group=CICGroup.GROUP_5, days_past_due=400
    )
    b = make_borrower(contracts=(c,), assessments=(a_past, a_future))
    f = extract(b, date(2026, 5, 14))
    assert f.worst_group_ever is CICGroup.GROUP_1  # GROUP_5 in October is invisible


def test_extract_filters_future_inquiries():
    c = make_contract(opened_at=date(2024, 1, 1))
    q_past = make_inquiry(inquired_at=date(2026, 5, 1))
    q_future = make_inquiry(inquired_at=date(2026, 8, 1))
    b = make_borrower(contracts=(c,), inquiries=(q_past, q_future))
    f = extract(b, date(2026, 5, 14))
    assert f.inquiries_6m == 1  # only the past one


def test_extract_filters_future_contracts():
    c_past = make_contract(contract_id="C-1", opened_at=date(2024, 1, 1))
    c_future = make_contract(contract_id="C-2", opened_at=date(2027, 1, 1))
    b = make_borrower(contracts=(c_past, c_future))
    f = extract(b, date(2026, 5, 14))
    assert f.active_contracts == 1
    assert f.months_since_last_credit_open is not None
    # last open = 2024-01-01; obs = 2026-05-14 → 28 months
    assert f.months_since_last_credit_open == 28


def test_extract_treats_closed_contracts_as_inactive():
    c_closed = make_contract(
        contract_id="C-1", opened_at=date(2024, 1, 1), closed_at=date(2025, 12, 1)
    )
    a = make_assessment(contract_id="C-1", as_of_month=date(2025, 11, 1))
    b = make_borrower(contracts=(c_closed,), assessments=(a,))
    f = extract(b, date(2026, 5, 14))
    assert f.active_contracts == 0
    assert f.current_max_group is None
    assert f.total_outstanding_principal_vnd == 0


# ------ Group-cascade / max ----------------------------------------------


def test_current_max_group_uses_worst_across_active_contracts():
    """Effective borrower group = max across active contracts (Điều 11)."""
    c1 = make_contract(contract_id="C-1", opened_at=date(2024, 1, 1))
    c2 = make_contract(
        contract_id="C-2", opened_at=date(2024, 1, 1), contract_type=ContractType.CREDIT_CARD
    )
    a1 = make_assessment(contract_id="C-1", as_of_month=date(2026, 5, 1), group=CICGroup.GROUP_1)
    a2 = make_assessment(
        contract_id="C-2", as_of_month=date(2026, 5, 1), group=CICGroup.GROUP_3, days_past_due=100
    )
    b = make_borrower(contracts=(c1, c2), assessments=(a1, a2))
    f = extract(b, date(2026, 5, 14))
    assert f.current_max_group is CICGroup.GROUP_3


def test_max_group_24m_window():
    """Assessments older than 24 months don't influence max_group_24m."""
    c = make_contract(opened_at=date(2022, 1, 1))
    # 2024-05 is exactly 24 months before 2026-05 → in window.
    in_window = make_assessment(
        as_of_month=date(2024, 6, 1), group=CICGroup.GROUP_4, days_past_due=200
    )
    # 2023-01 is 28 months before → out of 24m window but in worst_group_ever.
    pre_window = make_assessment(
        as_of_month=date(2023, 1, 1), group=CICGroup.GROUP_5, days_past_due=400
    )
    recent = make_assessment(as_of_month=date(2026, 5, 1), group=CICGroup.GROUP_1)
    b = make_borrower(contracts=(c,), assessments=(in_window, pre_window, recent))
    f = extract(b, date(2026, 5, 14))
    assert f.max_group_24m is CICGroup.GROUP_4
    assert f.worst_group_ever is CICGroup.GROUP_5


def test_months_in_group_2plus_counts_distinct_months():
    c = make_contract(opened_at=date(2024, 1, 1))
    # 3 contracts, all group 2 in same month → counts as 1 month.
    same_month = [
        make_assessment(as_of_month=date(2026, 3, 1), group=CICGroup.GROUP_2, days_past_due=20),
    ]
    different_months = [
        make_assessment(as_of_month=date(2026, 4, 1), group=CICGroup.GROUP_2, days_past_due=20),
        make_assessment(as_of_month=date(2026, 5, 1), group=CICGroup.GROUP_3, days_past_due=100),
    ]
    b = make_borrower(contracts=(c,), assessments=tuple(same_month + different_months))
    f = extract(b, date(2026, 5, 14))
    assert f.months_in_group_2plus_24m == 3


def test_months_in_group_2plus_excludes_group_1():
    c = make_contract(opened_at=date(2024, 1, 1))
    g1_only = [
        make_assessment(as_of_month=date(2026, m, 1), group=CICGroup.GROUP_1) for m in range(1, 6)
    ]
    b = make_borrower(contracts=(c,), assessments=tuple(g1_only))
    f = extract(b, date(2026, 5, 14))
    assert f.months_in_group_2plus_24m == 0


# ------ Exposure ----------------------------------------------------------


def test_total_outstanding_sums_latest_per_active_contract():
    c1 = make_contract(contract_id="C-1", opened_at=date(2024, 1, 1))
    c2 = make_contract(contract_id="C-2", opened_at=date(2024, 1, 1))
    # Stale assessment + recent one for C-1 → use the recent one.
    stale = make_assessment(contract_id="C-1", as_of_month=date(2025, 1, 1), principal=80_000_000)
    fresh = make_assessment(contract_id="C-1", as_of_month=date(2026, 4, 1), principal=40_000_000)
    c2_fresh = make_assessment(
        contract_id="C-2", as_of_month=date(2026, 4, 1), principal=20_000_000
    )
    b = make_borrower(contracts=(c1, c2), assessments=(stale, fresh, c2_fresh))
    f = extract(b, date(2026, 5, 14))
    assert f.total_outstanding_principal_vnd == 40_000_000 + 20_000_000


def test_unique_lenders_count():
    c1 = make_contract(contract_id="C-1", opened_at=date(2024, 1, 1), lender_bank="VCB")
    c2 = make_contract(contract_id="C-2", opened_at=date(2024, 1, 1), lender_bank="BIDV")
    c3 = make_contract(contract_id="C-3", opened_at=date(2024, 1, 1), lender_bank="VCB")  # dup
    b = make_borrower(contracts=(c1, c2, c3))
    f = extract(b, date(2026, 5, 14))
    assert f.unique_lenders == 2


def test_provision_estimate_uses_group_rates():
    c1 = make_contract(contract_id="C-1", opened_at=date(2024, 1, 1))
    c2 = make_contract(contract_id="C-2", opened_at=date(2024, 1, 1))
    # 100M @ group 2 (5%) + 100M @ group 5 (100%) = 5M + 100M = 105M provision.
    a1 = make_assessment(
        contract_id="C-1",
        as_of_month=date(2026, 5, 1),
        group=CICGroup.GROUP_2,
        principal=100_000_000,
        days_past_due=30,
    )
    a2 = make_assessment(
        contract_id="C-2",
        as_of_month=date(2026, 5, 1),
        group=CICGroup.GROUP_5,
        principal=100_000_000,
        days_past_due=400,
    )
    b = make_borrower(contracts=(c1, c2), assessments=(a1, a2))
    f = extract(b, date(2026, 5, 14))
    assert f.provision_estimate_vnd == 105_000_000


# ------ Inquiries ---------------------------------------------------------


def test_inquiry_window_counts_3m_6m_12m():
    c = make_contract(opened_at=date(2024, 1, 1))
    obs = date(2026, 5, 14)
    inqs = (
        make_inquiry(inquired_at=date(2026, 5, 1)),  # within 3m
        make_inquiry(inquired_at=date(2026, 4, 1)),  # within 3m
        make_inquiry(inquired_at=date(2025, 12, 1)),  # within 6m only
        make_inquiry(inquired_at=date(2025, 8, 1)),  # within 12m only
        make_inquiry(inquired_at=date(2024, 1, 1)),  # > 12m
    )
    b = make_borrower(contracts=(c,), inquiries=inqs)
    f = extract(b, obs)
    assert f.inquiries_3m == 2
    assert f.inquiries_6m == 3
    assert f.inquiries_12m == 4


def test_days_since_last_inquiry():
    c = make_contract(opened_at=date(2024, 1, 1))
    q = make_inquiry(inquired_at=date(2026, 5, 4))
    b = make_borrower(contracts=(c,), inquiries=(q,))
    f = extract(b, date(2026, 5, 14))
    assert f.days_since_last_inquiry == 10


def test_days_since_last_inquiry_none_when_no_inquiries():
    c = make_contract(opened_at=date(2024, 1, 1))
    b = make_borrower(contracts=(c,))
    f = extract(b, date(2026, 5, 14))
    assert f.days_since_last_inquiry is None


# ------ Product mix flags -------------------------------------------------


def test_product_mix_flags():
    contracts = (
        make_contract(
            contract_id="C-L", opened_at=date(2024, 1, 1), contract_type=ContractType.TERM_LOAN
        ),
        make_contract(
            contract_id="C-C", opened_at=date(2024, 1, 1), contract_type=ContractType.CREDIT_CARD
        ),
        make_contract(
            contract_id="C-O", opened_at=date(2024, 1, 1), contract_type=ContractType.OVERDRAFT
        ),
    )
    b = make_borrower(contracts=contracts)
    f = extract(b, date(2026, 5, 14))
    assert f.has_term_loan
    assert f.has_credit_card
    assert f.has_overdraft
    assert not f.has_mortgage
    assert not f.has_auto_loan
    assert not f.has_business_loan


def test_product_mix_only_considers_active_contracts():
    closed = make_contract(
        contract_id="C-M",
        opened_at=date(2024, 1, 1),
        closed_at=date(2025, 1, 1),
        contract_type=ContractType.MORTGAGE,
    )
    b = make_borrower(contracts=(closed,))
    f = extract(b, date(2026, 5, 14))
    assert not f.has_mortgage  # closed before obs → not active


# ------ DTI ---------------------------------------------------------------


def test_dti_none_when_income_missing():
    c = make_contract(opened_at=date(2024, 1, 1))
    a = make_assessment(as_of_month=date(2026, 5, 1), principal=50_000_000)
    b = make_borrower(contracts=(c,), assessments=(a,))
    f = extract(b, date(2026, 5, 14))
    assert f.dti_ratio is None


def test_dti_uses_term_loan_36month_payment():
    c = make_contract(
        contract_id="C-1", opened_at=date(2024, 1, 1), contract_type=ContractType.TERM_LOAN
    )
    a = make_assessment(as_of_month=date(2026, 5, 1), principal=36_000_000)  # → 1M/month
    b = make_borrower(contracts=(c,), assessments=(a,), monthly_income_vnd=10_000_000)
    f = extract(b, date(2026, 5, 14))
    assert f.dti_ratio is not None
    assert abs(f.dti_ratio - 0.10) < 1e-6


def test_dti_credit_card_uses_5pct_minimum_payment():
    c = make_contract(
        contract_id="C-1", opened_at=date(2024, 1, 1), contract_type=ContractType.CREDIT_CARD
    )
    a = make_assessment(as_of_month=date(2026, 5, 1), principal=20_000_000)  # 5 % = 1M
    b = make_borrower(contracts=(c,), assessments=(a,), monthly_income_vnd=10_000_000)
    f = extract(b, date(2026, 5, 14))
    assert f.dti_ratio is not None
    assert abs(f.dti_ratio - 0.10) < 1e-6


# ------ Tenure ------------------------------------------------------------


def test_months_since_first_credit():
    c1 = make_contract(contract_id="C-1", opened_at=date(2023, 5, 1))
    c2 = make_contract(contract_id="C-2", opened_at=date(2024, 8, 1))
    b = make_borrower(contracts=(c1, c2))
    f = extract(b, date(2026, 5, 14))
    # 2023-05 → 2026-05 = 36 months.
    assert f.months_since_first_credit == 36
    # last open 2024-08 → 2026-05 = 21 months.
    assert f.months_since_last_credit_open == 21


def test_tenure_none_for_no_contracts():
    b = make_borrower()
    f = extract(b, date(2026, 5, 14))
    assert f.months_since_first_credit is None
    assert f.months_since_last_credit_open is None
