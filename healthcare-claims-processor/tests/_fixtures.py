"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

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

DEFAULT_TS = datetime(2026, 5, 17, 9, 0, 0, tzinfo=VN_TZ)


def make_patient(**overrides: Any) -> Patient:
    defaults = {
        "patient_id": "P-001",
        "full_name": "Bệnh nhân Một",
        "date_of_birth": date(1990, 1, 1),
        "sex": "F",
        "province_code": "01",
    }
    defaults.update(overrides)
    return Patient(**defaults)  # type: ignore[arg-type]


def make_card(**overrides: Any) -> BHYTCard:
    defaults = {
        "card_number": "D40179012345678",  # D = employer; 4 = priority 4
        "category": ExemptionCategory.UU_TIEN_4,
        "valid_from": date(2024, 1, 1),
        "valid_to": date(2027, 1, 1),
    }
    defaults.update(overrides)
    return BHYTCard(**defaults)  # type: ignore[arg-type]


def make_diagnosis(**overrides: Any) -> Diagnosis:
    defaults = {
        "icd_code": "I10",
        "name_vi": "Tăng huyết áp",
        "is_primary": True,
    }
    defaults.update(overrides)
    return Diagnosis(**defaults)  # type: ignore[arg-type]


def make_item(**overrides: Any) -> ClaimItem:
    defaults = {
        "item_code": "KCB001",
        "name_vi": "Khám bệnh nội khoa",
        "unit_price_vnd": 50_000,
        "quantity": 1,
        "line_total_vnd": 50_000,
    }
    defaults.update(overrides)
    return ClaimItem(**defaults)  # type: ignore[arg-type]


def make_claim(**overrides: Any) -> Claim:
    items = overrides.pop("items", None) or (make_item(),)
    subtotal = overrides.pop("subtotal_vnd", None)
    if subtotal is None:
        subtotal = sum(it.line_total_vnd for it in items)
    defaults: dict[str, Any] = {
        "claim_id": "CL-001",
        "patient_id": "P-001",
        "card_number": "D40179012345678",
        "care_level": CareLevel.HUYEN,
        "service_kind": ServiceKind.OUTPATIENT,
        "has_referral": True,
        "same_province": True,
        "visited_at": DEFAULT_TS,
        "diagnoses": (make_diagnosis(),),
        "items": tuple(items),
        "subtotal_vnd": subtotal,
    }
    defaults.update(overrides)
    return Claim(**defaults)


__all__ = [
    "DEFAULT_TS",
    "make_card",
    "make_claim",
    "make_diagnosis",
    "make_item",
    "make_patient",
]
