"""Schema invariants + date helpers."""

from __future__ import annotations

from datetime import date

import pytest

from cicscore.schema import (
    ContractType,
    add_months,
    first_of_month,
    months_between,
)

from ._fixtures import (
    make_assessment,
    make_borrower,
    make_contract,
    make_inquiry,
)

# ------ CreditContract ----------------------------------------------------


def test_contract_happy_path():
    c = make_contract(original_amount=100_000_000)
    assert c.original_amount_vnd == 100_000_000


def test_contract_rejects_empty_fields():
    with pytest.raises(ValueError):
        make_contract(contract_id="")
    with pytest.raises(ValueError):
        make_contract(borrower_id="")
    with pytest.raises(ValueError):
        make_contract(lender_bank="")


def test_contract_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        make_contract(original_amount=0)
    with pytest.raises(ValueError):
        make_contract(original_amount=-1)


def test_contract_rejects_closed_before_opened():
    with pytest.raises(ValueError):
        make_contract(opened_at=date(2024, 6, 1), closed_at=date(2024, 1, 1))


def test_contract_is_active_on():
    c = make_contract(opened_at=date(2024, 1, 1), closed_at=date(2025, 6, 1))
    assert not c.is_active_on(date(2023, 12, 31))
    assert c.is_active_on(date(2024, 1, 1))
    assert c.is_active_on(date(2025, 5, 31))
    assert not c.is_active_on(date(2025, 6, 1))  # closed_at is exclusive


def test_contract_is_active_when_never_closed():
    c = make_contract(closed_at=None)
    assert c.is_active_on(date(2026, 5, 14))


# ------ GroupAssessment ---------------------------------------------------


def test_assessment_rejects_non_first_of_month():
    with pytest.raises(ValueError):
        make_assessment(as_of_month=date(2026, 5, 14))


def test_assessment_rejects_negative_principal():
    with pytest.raises(ValueError):
        make_assessment(as_of_month=date(2026, 5, 1), principal=-1)


def test_assessment_rejects_negative_interest():
    with pytest.raises(ValueError):
        make_assessment(as_of_month=date(2026, 5, 1), interest=-1)


def test_assessment_rejects_negative_dpd():
    with pytest.raises(ValueError):
        make_assessment(as_of_month=date(2026, 5, 1), days_past_due=-1)


# ------ Inquiry -----------------------------------------------------------


def test_inquiry_rejects_empty_fields():
    with pytest.raises(ValueError):
        make_inquiry(borrower_id="", inquired_at=date(2026, 5, 14))
    with pytest.raises(ValueError):
        make_inquiry(lender_bank="", inquired_at=date(2026, 5, 14))


# ------ Borrower ----------------------------------------------------------


def test_borrower_validates_contract_borrower_ids():
    other = make_contract(borrower_id="OTHER")
    with pytest.raises(ValueError):
        make_borrower(borrower_id="B-1", contracts=(other,))


def test_borrower_validates_assessment_contract_ids():
    a = make_assessment(contract_id="ZZZ", as_of_month=date(2026, 5, 1))
    with pytest.raises(ValueError):
        make_borrower(borrower_id="B-1", assessments=(a,))


def test_borrower_validates_inquiry_borrower_id():
    q = make_inquiry(borrower_id="OTHER", inquired_at=date(2026, 5, 1))
    with pytest.raises(ValueError):
        make_borrower(borrower_id="B-1", inquiries=(q,))


def test_borrower_rejects_negative_income():
    with pytest.raises(ValueError):
        make_borrower(monthly_income_vnd=-1)


def test_borrower_accepts_none_income():
    b = make_borrower(monthly_income_vnd=None)
    assert b.monthly_income_vnd is None


# ------ Date helpers ------------------------------------------------------


def test_first_of_month():
    assert first_of_month(date(2026, 5, 14)) == date(2026, 5, 1)
    assert first_of_month(date(2026, 1, 1)) == date(2026, 1, 1)


def test_add_months_basic():
    assert add_months(date(2026, 5, 14), 1) == date(2026, 6, 14)
    assert add_months(date(2026, 5, 14), -1) == date(2026, 4, 14)


def test_add_months_year_boundary():
    assert add_months(date(2026, 1, 15), -1) == date(2025, 12, 15)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_add_months_clamps_day_for_short_months():
    # 31 Jan + 1 month → 28 Feb (or 29 in leap years, but 2026 isn't leap)
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_months_between():
    assert months_between(date(2026, 5, 1), date(2026, 5, 1)) == 0
    assert months_between(date(2026, 5, 1), date(2024, 5, 1)) == 24
    assert months_between(date(2024, 5, 1), date(2026, 5, 1)) == -24


def test_contract_type_enum_values():
    expected = {"TERM_LOAN", "MORTGAGE", "AUTO_LOAN", "CREDIT_CARD", "OVERDRAFT", "BUSINESS_LOAN"}
    assert {ct.value for ct in ContractType} == expected
