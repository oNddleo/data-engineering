"""Hypothesis property tests."""

from __future__ import annotations

from datetime import date

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnbhyt.payout import compute
from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier


@given(
    card=st.sampled_from(list(CardClass)),
    tier=st.sampled_from(list(HospitalTier)),
    care=st.sampled_from(list(CareType)),
    in_net=st.booleans(),
    billed=st.integers(min_value=0, max_value=1_000_000_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_payout_plus_copay_equals_billed(
    card: CardClass,
    tier: HospitalTier,
    care: CareType,
    in_net: bool,
    billed: int,
) -> None:
    """Conservation invariant."""
    c = Claim(
        claim_id="X",
        patient_id="P",
        card_class=card,
        hospital_tier=tier,
        care_type=care,
        icd10="J18.9",
        billed_amount_vnd=billed,
        visited_on=date(2026, 3, 15),
        is_in_network=in_net,
    )
    p = compute(c)
    assert p.insurance_payout_vnd + p.patient_copay_vnd == billed


@given(
    card=st.sampled_from(list(CardClass)),
    tier=st.sampled_from(list(HospitalTier)),
    billed=st.integers(min_value=0, max_value=1_000_000_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_in_network_always_at_least_out_of_network(
    card: CardClass,
    tier: HospitalTier,
    billed: int,
) -> None:
    """In-network payout >= out-of-network payout for non-emergency care."""
    base = Claim(
        claim_id="X",
        patient_id="P",
        card_class=card,
        hospital_tier=tier,
        care_type=CareType.OUTPATIENT,
        icd10="J18.9",
        billed_amount_vnd=billed,
        visited_on=date(2026, 3, 15),
        is_in_network=True,
    )
    oon = Claim(
        claim_id="X",
        patient_id="P",
        card_class=card,
        hospital_tier=tier,
        care_type=CareType.OUTPATIENT,
        icd10="J18.9",
        billed_amount_vnd=billed,
        visited_on=date(2026, 3, 15),
        is_in_network=False,
    )
    assert compute(base).insurance_payout_vnd >= compute(oon).insurance_payout_vnd


@given(
    card=st.sampled_from(list(CardClass)),
    tier=st.sampled_from(list(HospitalTier)),
    billed=st.integers(min_value=0, max_value=1_000_000_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_emergency_equals_in_network(
    card: CardClass,
    tier: HospitalTier,
    billed: int,
) -> None:
    """Emergency out-of-network = in-network for the same card/tier."""
    em_oon = Claim(
        claim_id="X",
        patient_id="P",
        card_class=card,
        hospital_tier=tier,
        care_type=CareType.EMERGENCY,
        icd10="J18.9",
        billed_amount_vnd=billed,
        visited_on=date(2026, 3, 15),
        is_in_network=False,
    )
    in_net = Claim(
        claim_id="X",
        patient_id="P",
        card_class=card,
        hospital_tier=tier,
        care_type=CareType.EMERGENCY,
        icd10="J18.9",
        billed_amount_vnd=billed,
        visited_on=date(2026, 3, 15),
        is_in_network=True,
    )
    assert compute(em_oon).insurance_payout_vnd == compute(in_net).insurance_payout_vnd
