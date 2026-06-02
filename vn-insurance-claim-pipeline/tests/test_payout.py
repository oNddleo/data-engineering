"""Payout calculation."""

from __future__ import annotations

from datetime import date

from vnbhyt.payout import compute
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
        "is_in_network": True,
    }
    fields.update(overrides)
    return Claim(**fields)  # type: ignore[arg-type]


def test_in_network_employee_80pct() -> None:
    p = compute(_claim(card_class=CardClass.EMPLOYEE))
    assert p.effective_ratio == 0.80
    assert p.insurance_payout_vnd == 800_000
    assert p.patient_copay_vnd == 200_000


def test_in_network_poor_100pct() -> None:
    p = compute(_claim(card_class=CardClass.POOR))
    assert p.effective_ratio == 1.00
    assert p.insurance_payout_vnd == 1_000_000
    assert p.patient_copay_vnd == 0


def test_in_network_retiree_95pct() -> None:
    p = compute(_claim(card_class=CardClass.RETIREE))
    assert p.effective_ratio == 0.95
    assert p.insurance_payout_vnd == 950_000


def test_out_of_network_central_employee() -> None:
    """80% * 40% = 32% at central hospital out of network."""
    p = compute(
        _claim(
            card_class=CardClass.EMPLOYEE,
            hospital_tier=HospitalTier.CENTRAL,
            is_in_network=False,
        )
    )
    assert p.effective_ratio == 0.80 * 0.40
    assert p.insurance_payout_vnd == 320_000


def test_out_of_network_provincial_employee() -> None:
    """80% * 60% = 48% at provincial hospital out of network."""
    p = compute(
        _claim(
            card_class=CardClass.EMPLOYEE,
            hospital_tier=HospitalTier.PROVINCIAL,
            is_in_network=False,
        )
    )
    assert abs(p.effective_ratio - 0.48) < 1e-9
    assert p.insurance_payout_vnd == 480_000


def test_out_of_network_district_unaffected() -> None:
    """District hospitals are fully open — out-of-network doesn't reduce."""
    p = compute(
        _claim(
            card_class=CardClass.EMPLOYEE,
            hospital_tier=HospitalTier.DISTRICT,
            is_in_network=False,
        )
    )
    assert p.effective_ratio == 0.80


def test_emergency_overrides_out_of_network() -> None:
    """Emergency at any tier is fully covered as in-network."""
    p = compute(
        _claim(
            card_class=CardClass.EMPLOYEE,
            hospital_tier=HospitalTier.CENTRAL,
            care_type=CareType.EMERGENCY,
            is_in_network=False,
        )
    )
    assert p.effective_ratio == 0.80


def test_zero_bill() -> None:
    p = compute(_claim(billed_amount_vnd=0))
    assert p.insurance_payout_vnd == 0
    assert p.patient_copay_vnd == 0


def test_payout_plus_copay_equals_billed() -> None:
    """Conservation: payout + copay always reconstructs the billed amount."""
    p = compute(_claim(billed_amount_vnd=12_345_678))
    assert p.insurance_payout_vnd + p.patient_copay_vnd == 12_345_678


def test_payout_validates_ratio() -> None:
    """Constructing a Payout out of band still validates."""
    import pytest

    from vnbhyt.payout import Payout

    with pytest.raises(ValueError):
        Payout(
            claim_id="X",
            effective_ratio=1.5,
            insurance_payout_vnd=0,
            patient_copay_vnd=0,
        )
