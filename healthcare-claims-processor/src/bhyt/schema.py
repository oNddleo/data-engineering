"""BHYT (social health insurance) claim schema.

Models a Vietnamese health-insurance claim as the data flows from a
hospital's billing system into Vietnam Social Security (VSS) for
reimbursement. The shape follows **Quyết định 1399/QĐ-BYT (2014)**
and the subsequent reimbursement-rate tables in **Nghị định 146/2018/NĐ-CP**.

Three big concepts:

1. **Exemption category** — which "diện" the patient is in. Drives
   the base coverage rate (80%, 95%, 100%). Five categories per
   Article 22 of the Law on Health Insurance (2014):

   | Category | "Diện" | Coverage at the right level |
   | -------- | ------ | --------------------------- |
   | UU_TIEN_1 | Children < 6, ethnic minorities in poor zones | 100% |
   | UU_TIEN_2 | War veterans, revolution contributors          | 100% |
   | UU_TIEN_3 | Poor / near-poor households                    | 100% / 95% |
   | UU_TIEN_4 | Regular workers (employer-paid)                | 80% |
   | UU_TIEN_5 | Voluntary (self-paid)                          | 80% |

2. **Care level** ("tuyến" — referral tier). Driving the **referral
   penalty**: going straight to a higher tier without a referral
   drops coverage to 40% (TƯ), 60% (tỉnh), 100% (huyện).

   | Level | What it is                                          |
   | ----- | --------------------------------------------------- |
   | TU    | Central (Bạch Mai, Chợ Rẫy, …)                       |
   | TINH  | Provincial (Bệnh viện Đa khoa tỉnh)                  |
   | HUYEN | District (Bệnh viện Huyện)                           |
   | XA    | Commune health station                              |
   | OTHER | Privately-contracted facilities                     |

3. **Service kind** — outpatient vs inpatient. Inpatient triggers
   per-day caps and the K-DRG bundle methodology (not modelled here
   beyond the basic rate calculation).

All money is integer VND.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class ExemptionCategory(str, Enum):
    """Five 'diện' categories per the Law on Health Insurance Article 22."""

    UU_TIEN_1 = "UU_TIEN_1"  # 100% — children < 6, ethnic minorities in poor zones
    UU_TIEN_2 = "UU_TIEN_2"  # 100% — war veterans, revolution contributors
    UU_TIEN_3 = "UU_TIEN_3"  # 100/95% — poor / near-poor households
    UU_TIEN_4 = "UU_TIEN_4"  # 80%  — regular employer-paid
    UU_TIEN_5 = "UU_TIEN_5"  # 80%  — voluntary / self-paid


class CareLevel(str, Enum):
    """Hospital tier ("tuyến")."""

    TU = "TU"  # Central
    TINH = "TINH"  # Provincial
    HUYEN = "HUYEN"  # District
    XA = "XA"  # Commune
    OTHER = "OTHER"  # Private / contracted facility


class ServiceKind(str, Enum):
    """Outpatient vs inpatient — affects caps + K-DRG bundling."""

    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"


@dataclass(frozen=True, slots=True)
class Patient:
    """Insured patient demographics."""

    patient_id: str
    full_name: str
    date_of_birth: date
    sex: str  # "M" or "F" or "U"
    province_code: str  # for referral-penalty calculation when crossing tỉnh

    def __post_init__(self) -> None:
        if not self.patient_id:
            raise ValueError("patient_id must be non-empty")
        if not self.full_name:
            raise ValueError("full_name must be non-empty")
        if self.sex not in ("M", "F", "U"):
            raise ValueError(f"sex must be M/F/U, got {self.sex!r}")
        if not self.province_code:
            raise ValueError("province_code must be non-empty")

    def age_years_at(self, asof: date) -> int:
        """Age in completed years on ``asof``."""
        age = asof.year - self.date_of_birth.year
        if (asof.month, asof.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age


@dataclass(frozen=True, slots=True)
class BHYTCard:
    """VN health-insurance card. 15 characters: 2 letters + 13 digits."""

    card_number: str  # canonical uppercase
    category: ExemptionCategory
    valid_from: date
    valid_to: date  # exclusive

    def __post_init__(self) -> None:
        if not self.card_number:
            raise ValueError("card_number must be non-empty")
        if len(self.card_number) != 15:
            raise ValueError(f"card_number must be 15 characters, got {len(self.card_number)}")
        # Real VSS format (Decision 1351/QĐ-BHXH 2015): 1 scheme letter +
        # 1 priority digit (1-5) + 13 region/identifier digits.
        if not self.card_number[0].isalpha() or not self.card_number[0].isupper():
            raise ValueError(
                f"card_number[0] must be an uppercase letter, got {self.card_number[0]!r}"
            )
        if self.card_number[1] not in "12345":
            raise ValueError(
                f"card_number[1] must be a priority digit 1-5, got {self.card_number[1]!r}"
            )
        if not self.card_number[2:].isdigit():
            raise ValueError(f"card_number[2:] must be 13 digits, got {self.card_number[2:]!r}")
        if self.valid_from >= self.valid_to:
            raise ValueError(f"valid_from {self.valid_from} must be < valid_to {self.valid_to}")

    def is_active_on(self, day: date) -> bool:
        """``True`` if the card covers ``day`` (half-open interval)."""
        return self.valid_from <= day < self.valid_to


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """ICD-10-VN coded diagnosis on a claim."""

    icd_code: str  # e.g. "I10" (essential hypertension)
    name_vi: str  # Vietnamese diagnosis text
    is_primary: bool = True

    def __post_init__(self) -> None:
        if not self.icd_code:
            raise ValueError("icd_code must be non-empty")
        if not self.name_vi:
            raise ValueError("name_vi must be non-empty")
        # Loose ICD-10 format: letter + 2-3 digits + optional ".x".
        valid = (
            len(self.icd_code) >= 3
            and self.icd_code[0].isalpha()
            and self.icd_code[0].isupper()
            and all(c.isdigit() or c == "." for c in self.icd_code[1:])
        )
        if not valid:
            raise ValueError(f"icd_code {self.icd_code!r} doesn't match ICD-10 format")


@dataclass(frozen=True, slots=True)
class ClaimItem:
    """One line on a claim — a service, drug, or supply."""

    item_code: str
    name_vi: str
    unit_price_vnd: int
    quantity: int
    line_total_vnd: int  # validator confirms = quantity × unit_price

    def __post_init__(self) -> None:
        if not self.item_code:
            raise ValueError("item_code must be non-empty")
        if not self.name_vi:
            raise ValueError("name_vi must be non-empty")
        if self.unit_price_vnd < 0:
            raise ValueError(f"unit_price_vnd must be >= 0, got {self.unit_price_vnd}")
        if self.quantity < 1:
            raise ValueError(f"quantity must be >= 1, got {self.quantity}")
        if self.line_total_vnd < 0:
            raise ValueError(f"line_total_vnd must be >= 0, got {self.line_total_vnd}")


@dataclass(frozen=True, slots=True)
class Claim:
    """One submitted claim header + lines."""

    claim_id: str
    patient_id: str
    card_number: str
    care_level: CareLevel
    service_kind: ServiceKind
    has_referral: bool  # was a proper referral issued?
    same_province: bool  # is the facility in the patient's home province?
    visited_at: datetime
    diagnoses: tuple[Diagnosis, ...]
    items: tuple[ClaimItem, ...]
    subtotal_vnd: int  # sum of line_total

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if not self.patient_id:
            raise ValueError("patient_id must be non-empty")
        if not self.card_number:
            raise ValueError("card_number must be non-empty")
        if self.visited_at.tzinfo is None:
            raise ValueError("visited_at must be timezone-aware")
        if not self.diagnoses:
            raise ValueError("at least one diagnosis is required")
        n_primary = sum(1 for d in self.diagnoses if d.is_primary)
        if n_primary != 1:
            raise ValueError(f"exactly one primary diagnosis required, got {n_primary}")
        if not self.items:
            raise ValueError("at least one item is required")
        if self.subtotal_vnd < 0:
            raise ValueError(f"subtotal_vnd must be >= 0, got {self.subtotal_vnd}")


@dataclass(frozen=True, slots=True)
class Reimbursement:
    """Result of running a claim through the calculator."""

    claim_id: str
    subtotal_vnd: int
    coverage_rate_bps: int  # basis points: 8000 = 80%
    referral_penalty_bps: int  # applied multiplicatively on top
    insurer_pays_vnd: int  # what BHYT (VSS) pays
    patient_pays_vnd: int  # co-pay
    notes: tuple[str, ...] = ()


__all__ = [
    "VN_TZ",
    "BHYTCard",
    "CareLevel",
    "Claim",
    "ClaimItem",
    "Diagnosis",
    "ExemptionCategory",
    "Patient",
    "Reimbursement",
    "ServiceKind",
]
