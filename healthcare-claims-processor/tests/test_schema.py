"""Schema invariants."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from bhyt.schema import (
    BHYTCard,
    CareLevel,
    Diagnosis,
    ExemptionCategory,
    ServiceKind,
)

from ._fixtures import DEFAULT_TS, make_card, make_claim, make_diagnosis, make_patient


def test_exemption_category_five_values():
    assert {c.value for c in ExemptionCategory} == {
        "UU_TIEN_1",
        "UU_TIEN_2",
        "UU_TIEN_3",
        "UU_TIEN_4",
        "UU_TIEN_5",
    }


def test_care_level_five_values():
    assert {c.value for c in CareLevel} == {"TU", "TINH", "HUYEN", "XA", "OTHER"}


def test_service_kind_two_values():
    assert {s.value for s in ServiceKind} == {"OUTPATIENT", "INPATIENT"}


def test_patient_rejects_empty_id():
    with pytest.raises(ValueError):
        make_patient(patient_id="")


def test_patient_rejects_invalid_sex():
    with pytest.raises(ValueError, match="sex"):
        make_patient(sex="X")


def test_patient_age_computed_correctly():
    p = make_patient(date_of_birth=date(1990, 6, 15))
    assert p.age_years_at(date(2026, 6, 14)) == 35  # birthday tomorrow
    assert p.age_years_at(date(2026, 6, 15)) == 36  # on birthday
    assert p.age_years_at(date(2026, 6, 16)) == 36


def test_card_rejects_short_number():
    with pytest.raises(ValueError, match="15 characters"):
        make_card(card_number="D40179")


def test_card_rejects_non_letter_first_char():
    with pytest.raises(ValueError, match="uppercase letter"):
        make_card(card_number="140179012345678")


def test_card_rejects_non_priority_second_char():
    with pytest.raises(ValueError, match="priority digit"):
        make_card(card_number="DA0179012345678")


def test_card_rejects_invalid_priority_digit():
    with pytest.raises(ValueError, match="priority digit"):
        make_card(card_number="D60179012345678")  # 6 is out of 1-5


def test_card_rejects_non_digit_suffix():
    with pytest.raises(ValueError, match="13 digits"):
        make_card(card_number="D4017901234567A")


def test_card_rejects_inverted_validity():
    with pytest.raises(ValueError):
        BHYTCard(
            card_number="D40179012345678",
            category=ExemptionCategory.UU_TIEN_4,
            valid_from=date(2027, 1, 1),
            valid_to=date(2024, 1, 1),
        )


def test_card_is_active_on_check():
    card = make_card(
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 1, 1),
    )
    assert card.is_active_on(date(2025, 6, 1)) is True
    assert card.is_active_on(date(2024, 1, 1)) is True
    assert card.is_active_on(date(2023, 12, 31)) is False
    assert card.is_active_on(date(2027, 1, 1)) is False  # exclusive upper


def test_diagnosis_rejects_invalid_icd():
    with pytest.raises(ValueError, match="ICD-10"):
        Diagnosis(icd_code="abc", name_vi="bad")


def test_diagnosis_accepts_subcode():
    d = Diagnosis(icd_code="E11.9", name_vi="Diabetes")
    assert d.icd_code == "E11.9"


def test_claim_rejects_no_diagnoses():
    with pytest.raises(ValueError, match="diagnosis"):
        make_claim(diagnoses=())


def test_claim_rejects_two_primary_diagnoses():
    with pytest.raises(ValueError, match="primary"):
        make_claim(
            diagnoses=(
                make_diagnosis(icd_code="I10", is_primary=True),
                make_diagnosis(icd_code="E11", is_primary=True),
            )
        )


def test_claim_rejects_no_primary_diagnosis():
    with pytest.raises(ValueError, match="primary"):
        make_claim(diagnoses=(make_diagnosis(is_primary=False),))


def test_claim_rejects_naive_visited_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_claim(visited_at=datetime(2026, 5, 17, 9, 0))


def test_claim_default_passes():
    """Sanity — the fixture builds a legal default claim."""
    c = make_claim()
    assert c.claim_id == "CL-001"
    assert len(c.diagnoses) == 1
    assert c.visited_at == DEFAULT_TS
