"""Claim validation."""

from __future__ import annotations

from datetime import date

import pytest

from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier


def _claim(**overrides: object) -> Claim:
    fields: dict[str, object] = {
        "claim_id": "C-001",
        "patient_id": "P-001",
        "card_class": CardClass.EMPLOYEE,
        "hospital_tier": HospitalTier.DISTRICT,
        "care_type": CareType.OUTPATIENT,
        "icd10": "J18.9",
        "billed_amount_vnd": 1_000_000,
        "visited_on": date(2026, 3, 15),
    }
    fields.update(overrides)
    return Claim(**fields)  # type: ignore[arg-type]


def test_basic() -> None:
    c = _claim()
    assert c.is_in_network is True


def test_rejects_empty_ids() -> None:
    with pytest.raises(ValueError):
        _claim(claim_id="")
    with pytest.raises(ValueError):
        _claim(patient_id="")


def test_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        _claim(billed_amount_vnd=-1)


def test_zero_amount_allowed() -> None:
    """Zero-cost visits do happen (e.g. only a referral)."""
    c = _claim(billed_amount_vnd=0)
    assert c.billed_amount_vnd == 0


@pytest.mark.parametrize("good", ["J18.9", "A09", "O80.0", "B34.2", "M54.5", "Z00.0"])
def test_accepts_valid_icd10(good: str) -> None:
    c = _claim(icd10=good)
    assert c.icd10 == good


@pytest.mark.parametrize("bad", ["", "j18.9", "1J8.9", "JJJ", "J1.9", "J18.", "J18.A"])
def test_rejects_invalid_icd10(bad: str) -> None:
    with pytest.raises(ValueError):
        _claim(icd10=bad)


def test_frozen() -> None:
    c = _claim()
    with pytest.raises(Exception):
        c.billed_amount_vnd = 0  # type: ignore[misc]
