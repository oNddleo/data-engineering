"""Deterministic synthetic claim generator."""

from __future__ import annotations

import random
from datetime import date, timedelta

from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier

# Common ICD-10 codes seen in VN primary care (top respiratory, GI,
# diabetes, hypertension, post-natal).
_ICD10S: tuple[str, ...] = (
    "J18.9",  # pneumonia, unspecified
    "J06.9",  # acute upper respiratory infection
    "A09",  # GI infectious diarrhoea
    "I10",  # essential hypertension
    "E11.9",  # T2 diabetes
    "K29.7",  # gastritis
    "M54.5",  # low back pain
    "O80.0",  # spontaneous vertex delivery
    "B34.2",  # coronavirus infection, unspecified
    "Z00.0",  # general adult medical examination
)


def generate(n: int = 100, seed: int = 0) -> list[Claim]:
    """Generate ``n`` synthetic BHYT claims."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    out: list[Claim] = []
    base_date = date(2026, 1, 1)
    for i in range(n):
        card = rng.choice(list(CardClass))
        tier = rng.choices(
            list(HospitalTier),
            weights=[1, 3, 5, 2],  # mostly district / provincial
            k=1,
        )[0]
        care = rng.choices(
            list(CareType),
            weights=[6, 3, 1],  # mostly outpatient
            k=1,
        )[0]
        # 80% of claims are in-tuyến.
        in_net = rng.random() < 0.80
        out.append(
            Claim(
                claim_id=f"C-{i:06d}",
                patient_id=f"P-{rng.randrange(10_000):05d}",
                card_class=card,
                hospital_tier=tier,
                care_type=care,
                icd10=rng.choice(_ICD10S),
                billed_amount_vnd=rng.randint(100_000, 50_000_000),
                visited_on=base_date + timedelta(days=rng.randint(0, 364)),
                is_in_network=in_net,
            )
        )
    return out


__all__ = ["generate"]
