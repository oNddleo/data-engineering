"""BHYT payout calculator.

Three rates feed into the final payout:

1. **Base coverage** (``card_class``) — 100 / 95 / 80 % per BHYT rules.
2. **Out-of-network reduction** (``trái tuyến``) — multiplies the
   base by 40 / 60 / 100 % at central / provincial / district hospitals.
   Communes have no out-of-network concept (any patient can use).
3. **Care-type adjustment** — emergency care is always treated as
   in-network regardless of the registered hospital.

Final payout to the hospital = ``billed × effective_ratio``.
Patient co-pay = ``billed × (1 - effective_ratio)``.

All amounts are integer VND; we use ``round`` to avoid float drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier

# Base coverage ratio by card class.
_BASE_RATIO: dict[CardClass, float] = {
    CardClass.POOR: 1.00,
    CardClass.NEAR_POOR: 1.00,
    CardClass.CHILD_U6: 1.00,
    CardClass.RETIREE: 0.95,
    CardClass.STUDENT: 0.80,
    CardClass.EMPLOYEE: 0.80,
    CardClass.OTHER: 0.80,
}

# Out-of-network (trái tuyến) reduction by hospital tier.
_OUT_OF_NETWORK_RATIO: dict[HospitalTier, float] = {
    HospitalTier.CENTRAL: 0.40,
    HospitalTier.PROVINCIAL: 0.60,
    HospitalTier.DISTRICT: 1.00,  # district is fully open
    HospitalTier.COMMUNE: 1.00,
}


@dataclass(frozen=True, slots=True)
class Payout:
    """Computed payout for a single claim."""

    claim_id: str
    effective_ratio: float
    insurance_payout_vnd: int
    patient_copay_vnd: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.effective_ratio <= 1.0:
            raise ValueError("effective_ratio must be in [0, 1]")


def compute(claim: Claim) -> Payout:
    """Compute the BHYT payout for a single claim."""
    base = _BASE_RATIO[claim.card_class]
    # Emergencies are always treated as in-network.
    if claim.is_in_network or claim.care_type == CareType.EMERGENCY:
        effective = base
    else:
        out_mult = _OUT_OF_NETWORK_RATIO[claim.hospital_tier]
        effective = base * out_mult

    payout = round(claim.billed_amount_vnd * effective)
    copay = claim.billed_amount_vnd - payout
    return Payout(
        claim_id=claim.claim_id,
        effective_ratio=effective,
        insurance_payout_vnd=payout,
        patient_copay_vnd=copay,
    )


__all__ = ["Payout", "compute"]
