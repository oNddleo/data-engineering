"""VN BHYT (Bảo hiểm Y tế) claim schema.

BHYT is VN's universal health insurance scheme — coverage depends on:

* **Card class** (``Mã đối tượng``) — 100 % coverage for poor / ethnic /
  veteran groups (HN/CC/...), 95 % for retirees and near-poor, 80 %
  for ordinary employees and students.
* **Hospital tier** (``Tuyến``) — central, provincial, district,
  commune. Going outside your registered hospital ("trái tuyến")
  reduces coverage.
* **In-network ratio** — for trái tuyến, you get **40 % of the
  in-tuyến rate** at central hospitals, **60 %** at provincial,
  **100 %** at district.

This module models the schema; ``payout.compute`` does the math.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class CardClass(str, Enum):
    """BHYT card class — drives the base coverage ratio."""

    POOR = "HN"  # hộ nghèo — 100%
    NEAR_POOR = "CN"  # cận nghèo — 100% (per 2024 update)
    RETIREE = "HT"  # hưu trí — 95%
    STUDENT = "HS"  # học sinh / sinh viên — 80%
    EMPLOYEE = "DN"  # nhân viên doanh nghiệp — 80%
    CHILD_U6 = "TE"  # trẻ em dưới 6 tuổi — 100%
    OTHER = "OT"  # ordinary — 80%


class HospitalTier(str, Enum):
    """Hospital tier (tuyến)."""

    CENTRAL = "central"  # tuyến trung ương — Bạch Mai, K, …
    PROVINCIAL = "provincial"  # tuyến tỉnh
    DISTRICT = "district"  # tuyến huyện
    COMMUNE = "commune"  # tuyến xã


class CareType(str, Enum):
    OUTPATIENT = "outpatient"  # ngoại trú
    INPATIENT = "inpatient"  # nội trú
    EMERGENCY = "emergency"  # cấp cứu


@dataclass(frozen=True, slots=True)
class Claim:
    """One BHYT claim line (one visit / admission)."""

    claim_id: str
    patient_id: str
    card_class: CardClass
    hospital_tier: HospitalTier
    care_type: CareType
    icd10: str  # primary diagnosis (e.g. "J18.9")
    billed_amount_vnd: int  # total billable to insurance + patient
    visited_on: date
    is_in_network: bool = True  # đúng tuyến

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if not self.patient_id:
            raise ValueError("patient_id must be non-empty")
        if self.billed_amount_vnd < 0:
            raise ValueError("billed_amount_vnd must be >= 0")
        if not _is_valid_icd10(self.icd10):
            raise ValueError(f"icd10 must be a valid ICD-10 code, got {self.icd10!r}")


def _is_valid_icd10(code: str) -> bool:
    """Loose ICD-10 shape check: letter + 2 digits + optional .digit[s].

    Real ICD-10 has a frozen alphabet & detailed grammar, but the
    shape ``A00`` / ``A00.0`` / ``A00.99`` covers >99 % of real codes.
    """
    if not code or len(code) < 3:
        return False
    if not (code[0].isalpha() and code[0].isupper()):
        return False
    if not (code[1].isdigit() and code[2].isdigit()):
        return False
    if len(code) == 3:
        return True
    if code[3] != ".":
        return False
    return all(c.isdigit() for c in code[4:]) and 1 <= len(code) - 4 <= 4


__all__ = [
    "CardClass",
    "CareType",
    "Claim",
    "HospitalTier",
]
