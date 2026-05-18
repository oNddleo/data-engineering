"""JSONL codec for patients, cards, claims, reimbursements."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING

from bhyt.schema import (
    BHYTCard,
    CareLevel,
    Claim,
    ClaimItem,
    Diagnosis,
    ExemptionCategory,
    Patient,
    Reimbursement,
    ServiceKind,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def patient_to_dict(p: Patient) -> dict[str, object]:
    return {
        "patient_id": p.patient_id,
        "full_name": p.full_name,
        "date_of_birth": p.date_of_birth.isoformat(),
        "sex": p.sex,
        "province_code": p.province_code,
    }


def patient_from_dict(d: dict[str, object]) -> Patient:
    return Patient(
        patient_id=_require_str(d, "patient_id"),
        full_name=_require_str(d, "full_name"),
        date_of_birth=date.fromisoformat(_require_str(d, "date_of_birth")),
        sex=_require_str(d, "sex"),
        province_code=_require_str(d, "province_code"),
    )


def card_to_dict(c: BHYTCard) -> dict[str, object]:
    return {
        "card_number": c.card_number,
        "category": c.category.value,
        "valid_from": c.valid_from.isoformat(),
        "valid_to": c.valid_to.isoformat(),
    }


def card_from_dict(d: dict[str, object]) -> BHYTCard:
    return BHYTCard(
        card_number=_require_str(d, "card_number"),
        category=ExemptionCategory(_require_str(d, "category")),
        valid_from=date.fromisoformat(_require_str(d, "valid_from")),
        valid_to=date.fromisoformat(_require_str(d, "valid_to")),
    )


def _diagnosis_to_dict(d: Diagnosis) -> dict[str, object]:
    return {"icd_code": d.icd_code, "name_vi": d.name_vi, "is_primary": d.is_primary}


def _diagnosis_from_dict(d: dict[str, object]) -> Diagnosis:
    return Diagnosis(
        icd_code=_require_str(d, "icd_code"),
        name_vi=_require_str(d, "name_vi"),
        is_primary=_require_bool(d, "is_primary") if "is_primary" in d else True,
    )


def _item_to_dict(i: ClaimItem) -> dict[str, object]:
    return {
        "item_code": i.item_code,
        "name_vi": i.name_vi,
        "unit_price_vnd": i.unit_price_vnd,
        "quantity": i.quantity,
        "line_total_vnd": i.line_total_vnd,
    }


def _item_from_dict(d: dict[str, object]) -> ClaimItem:
    return ClaimItem(
        item_code=_require_str(d, "item_code"),
        name_vi=_require_str(d, "name_vi"),
        unit_price_vnd=_require_int(d, "unit_price_vnd"),
        quantity=_require_int(d, "quantity"),
        line_total_vnd=_require_int(d, "line_total_vnd"),
    )


def claim_to_dict(c: Claim) -> dict[str, object]:
    return {
        "claim_id": c.claim_id,
        "patient_id": c.patient_id,
        "card_number": c.card_number,
        "care_level": c.care_level.value,
        "service_kind": c.service_kind.value,
        "has_referral": c.has_referral,
        "same_province": c.same_province,
        "visited_at": c.visited_at.isoformat(),
        "diagnoses": [_diagnosis_to_dict(d) for d in c.diagnoses],
        "items": [_item_to_dict(i) for i in c.items],
        "subtotal_vnd": c.subtotal_vnd,
    }


def claim_from_dict(d: dict[str, object]) -> Claim:
    raw_diag = d.get("diagnoses")
    raw_items = d.get("items")
    if not isinstance(raw_diag, list):
        raise TypeError("diagnoses must be a list")
    if not isinstance(raw_items, list):
        raise TypeError("items must be a list")
    return Claim(
        claim_id=_require_str(d, "claim_id"),
        patient_id=_require_str(d, "patient_id"),
        card_number=_require_str(d, "card_number"),
        care_level=CareLevel(_require_str(d, "care_level")),
        service_kind=ServiceKind(_require_str(d, "service_kind")),
        has_referral=_require_bool(d, "has_referral"),
        same_province=_require_bool(d, "same_province"),
        visited_at=datetime.fromisoformat(_require_str(d, "visited_at")),
        diagnoses=tuple(_diagnosis_from_dict(x) for x in raw_diag if isinstance(x, dict)),
        items=tuple(_item_from_dict(x) for x in raw_items if isinstance(x, dict)),
        subtotal_vnd=_require_int(d, "subtotal_vnd"),
    )


def reimb_to_dict(r: Reimbursement) -> dict[str, object]:
    return {
        "claim_id": r.claim_id,
        "subtotal_vnd": r.subtotal_vnd,
        "coverage_rate_bps": r.coverage_rate_bps,
        "referral_penalty_bps": r.referral_penalty_bps,
        "insurer_pays_vnd": r.insurer_pays_vnd,
        "patient_pays_vnd": r.patient_pays_vnd,
        "notes": list(r.notes),
    }


def reimb_from_dict(d: dict[str, object]) -> Reimbursement:
    raw_notes = d.get("notes", [])
    if not isinstance(raw_notes, list):
        raise TypeError("notes must be a list")
    notes = tuple(n for n in raw_notes if isinstance(n, str))
    return Reimbursement(
        claim_id=_require_str(d, "claim_id"),
        subtotal_vnd=_require_int(d, "subtotal_vnd"),
        coverage_rate_bps=_require_int(d, "coverage_rate_bps"),
        referral_penalty_bps=_require_int(d, "referral_penalty_bps"),
        insurer_pays_vnd=_require_int(d, "insurer_pays_vnd"),
        patient_pays_vnd=_require_int(d, "patient_pays_vnd"),
        notes=notes,
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_patients(items: Iterable[Patient]) -> str:
    return _dump(patient_to_dict(p) for p in items)


def dump_cards(items: Iterable[BHYTCard]) -> str:
    return _dump(card_to_dict(c) for c in items)


def dump_claims(items: Iterable[Claim]) -> str:
    return _dump(claim_to_dict(c) for c in items)


def dump_reimbursements(items: Iterable[Reimbursement]) -> str:
    return _dump(reimb_to_dict(r) for r in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_patients(text: str) -> list[Patient]:
    return [patient_from_dict(d) for d in _iter_lines(text)]


def load_cards(text: str) -> list[BHYTCard]:
    return [card_from_dict(d) for d in _iter_lines(text)]


def load_claims(text: str) -> list[Claim]:
    return [claim_from_dict(d) for d in _iter_lines(text)]


def load_reimbursements(text: str) -> list[Reimbursement]:
    return [reimb_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "card_from_dict",
    "card_to_dict",
    "claim_from_dict",
    "claim_to_dict",
    "dump_cards",
    "dump_claims",
    "dump_patients",
    "dump_reimbursements",
    "load_cards",
    "load_claims",
    "load_patients",
    "load_reimbursements",
    "patient_from_dict",
    "patient_to_dict",
    "reimb_from_dict",
    "reimb_to_dict",
]
