"""Seeded synthetic BHYT claims for testing.

Generates a realistic mix of outpatient and inpatient claims with:

* Real-looking card numbers (valid format, decodable prefix).
* Diagnoses sampled from the bundled ICD-10-VN subset.
* Care levels weighted toward HUYEN + TINH (most claim volume).
* Referral status correlated with care level (TƯ visits without
  referral are realistic but rarer).
* Province-mismatch sprinkled in to exercise the penalty path.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from bhyt.icd10vn import bundled_codes
from bhyt.schema import (
    VN_TZ,
    BHYTCard,
    CareLevel,
    Claim,
    ClaimItem,
    Diagnosis,
    ExemptionCategory,
    Patient,
    ServiceKind,
)

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)

_PROVINCE_CODES = ("01", "26", "31", "48", "75", "79", "92")
_SCHEME_LETTERS = ("D", "H", "T", "C", "G", "X")
_PRIORITY_LETTERS = ("1", "2", "3", "4", "5")
_CATEGORY_BY_PRIORITY = {
    "1": ExemptionCategory.UU_TIEN_1,
    "2": ExemptionCategory.UU_TIEN_2,
    "3": ExemptionCategory.UU_TIEN_3,
    "4": ExemptionCategory.UU_TIEN_4,
    "5": ExemptionCategory.UU_TIEN_5,
}


def _make_card_number(rng: random.Random) -> tuple[str, ExemptionCategory]:
    """Build a valid card number + return the matching category."""
    scheme = rng.choice(_SCHEME_LETTERS)
    priority = rng.choice(_PRIORITY_LETTERS)
    province = rng.choice(_PROVINCE_CODES)
    suffix = "".join(str(rng.randint(0, 9)) for _ in range(11))
    return scheme + priority + province + suffix, _CATEGORY_BY_PRIORITY[priority]


def _service_lines(rng: random.Random, claim_id: str, n_lines: int) -> tuple[list[ClaimItem], int]:
    """Generate ``n_lines`` plausible service / drug / supply items."""
    items: list[ClaimItem] = []
    services = (
        ("KCB001", "Khám bệnh nội khoa", 50_000),
        ("KCB002", "Khám bệnh ngoại khoa", 60_000),
        ("XN_CTM", "Xét nghiệm công thức máu", 45_000),
        ("XN_NTV", "Tổng phân tích nước tiểu", 35_000),
        ("CDHA01", "Siêu âm bụng tổng quát", 110_000),
        ("CDHA02", "X-quang tim phổi thẳng", 65_000),
        ("THUO01", "Paracetamol 500mg", 1_000),
        ("THUO02", "Amoxicillin 500mg", 2_500),
        ("VATTU01", "Băng gạc tiêu chuẩn", 5_000),
    )
    for i in range(n_lines):
        code, name, base_price = rng.choice(services)
        qty = rng.choice((1, 1, 1, 2, 3, 5, 10))
        items.append(
            ClaimItem(
                item_code=f"{code}-{claim_id[-4:]}-{i:02d}",
                name_vi=name,
                unit_price_vnd=base_price,
                quantity=qty,
                line_total_vnd=base_price * qty,
            )
        )
    subtotal = sum(it.line_total_vnd for it in items)
    return items, subtotal


def generate(
    *,
    n_patients: int = 30,
    n_claims: int = 60,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Patient], list[BHYTCard], list[Claim]]:
    """Generate ``(patients, cards, claims)``."""
    if n_patients < 1:
        raise ValueError("n_patients must be >= 1")
    if n_claims < 1:
        raise ValueError("n_claims must be >= 1")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    patients: list[Patient] = []
    cards: list[BHYTCard] = []
    cards_by_patient: dict[str, str] = {}

    for i in range(n_patients):
        province = rng.choice(_PROVINCE_CODES)
        patient_id = f"P-{i:06d}"
        dob = date(rng.randint(1950, 2020), rng.randint(1, 12), rng.randint(1, 28))
        patients.append(
            Patient(
                patient_id=patient_id,
                full_name=f"Bệnh nhân {i + 1}",
                date_of_birth=dob,
                sex=rng.choice(("M", "F")),
                province_code=province,
            )
        )
        card_number, category = _make_card_number(rng)
        cards.append(
            BHYTCard(
                card_number=card_number,
                category=category,
                valid_from=date(2024, 1, 1),
                valid_to=date(2027, 1, 1),
            )
        )
        cards_by_patient[patient_id] = card_number

    codes = bundled_codes()
    claims: list[Claim] = []
    care_levels = (
        CareLevel.HUYEN,
        CareLevel.HUYEN,
        CareLevel.TINH,
        CareLevel.TINH,
        CareLevel.TU,
        CareLevel.XA,
        CareLevel.OTHER,
    )

    for j in range(n_claims):
        patient = rng.choice(patients)
        n_dx = rng.randint(1, 2)
        chosen = rng.sample(codes, n_dx)
        diagnoses = tuple(
            Diagnosis(
                icd_code=c.code,
                name_vi=c.name_vi,
                is_primary=(idx == 0),
            )
            for idx, c in enumerate(chosen)
        )
        care_level = rng.choice(care_levels)
        kind = rng.choice((ServiceKind.OUTPATIENT, ServiceKind.OUTPATIENT, ServiceKind.INPATIENT))
        # Referral: 70% have one when going to TU/TINH; always at HUYEN/XA.
        has_referral = rng.random() < 0.70 if care_level in (CareLevel.TU, CareLevel.TINH) else True
        same_province = rng.random() < 0.85
        n_lines = rng.randint(2, 6)
        items, subtotal = _service_lines(rng, f"CL-{j:06d}", n_lines)
        claims.append(
            Claim(
                claim_id=f"CL-{j:06d}",
                patient_id=patient.patient_id,
                card_number=cards_by_patient[patient.patient_id],
                care_level=care_level,
                service_kind=kind,
                has_referral=has_referral,
                same_province=same_province,
                visited_at=base + timedelta(hours=j * 4),
                diagnoses=diagnoses,
                items=tuple(items),
                subtotal_vnd=subtotal,
            )
        )

    return patients, cards, claims


__all__ = ["generate"]
