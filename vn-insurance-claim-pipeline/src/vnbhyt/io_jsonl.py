"""JSONL codec for claims + payouts."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from vnbhyt.payout import Payout
from vnbhyt.schema import CardClass, CareType, Claim, HospitalTier

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


def _opt_bool(d: dict[str, object], key: str, default: bool = True) -> bool:
    v = d.get(key, default)
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def _require_float(d: dict[str, object], key: str) -> float:
    v = d[key]
    if not isinstance(v, int | float) or isinstance(v, bool):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


def claim_to_dict(c: Claim) -> dict[str, object]:
    return {
        "claim_id": c.claim_id,
        "patient_id": c.patient_id,
        "card_class": c.card_class.value,
        "hospital_tier": c.hospital_tier.value,
        "care_type": c.care_type.value,
        "icd10": c.icd10,
        "billed_amount_vnd": c.billed_amount_vnd,
        "visited_on": c.visited_on.isoformat(),
        "is_in_network": c.is_in_network,
    }


def claim_from_dict(d: dict[str, object]) -> Claim:
    return Claim(
        claim_id=_require_str(d, "claim_id"),
        patient_id=_require_str(d, "patient_id"),
        card_class=CardClass(_require_str(d, "card_class")),
        hospital_tier=HospitalTier(_require_str(d, "hospital_tier")),
        care_type=CareType(_require_str(d, "care_type")),
        icd10=_require_str(d, "icd10"),
        billed_amount_vnd=_require_int(d, "billed_amount_vnd"),
        visited_on=date.fromisoformat(_require_str(d, "visited_on")),
        is_in_network=_opt_bool(d, "is_in_network"),
    )


def payout_to_dict(p: Payout) -> dict[str, object]:
    return {
        "claim_id": p.claim_id,
        "effective_ratio": p.effective_ratio,
        "insurance_payout_vnd": p.insurance_payout_vnd,
        "patient_copay_vnd": p.patient_copay_vnd,
    }


def payout_from_dict(d: dict[str, object]) -> Payout:
    return Payout(
        claim_id=_require_str(d, "claim_id"),
        effective_ratio=_require_float(d, "effective_ratio"),
        insurance_payout_vnd=_require_int(d, "insurance_payout_vnd"),
        patient_copay_vnd=_require_int(d, "patient_copay_vnd"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_claims(items: Iterable[Claim]) -> str:
    return _dump(claim_to_dict(c) for c in items)


def dump_payouts(items: Iterable[Payout]) -> str:
    return _dump(payout_to_dict(p) for p in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_claims(text: str) -> list[Claim]:
    return [claim_from_dict(d) for d in _iter_lines(text)]


def load_payouts(text: str) -> list[Payout]:
    return [payout_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "claim_from_dict",
    "claim_to_dict",
    "dump_claims",
    "dump_payouts",
    "load_claims",
    "load_payouts",
    "payout_from_dict",
    "payout_to_dict",
]
