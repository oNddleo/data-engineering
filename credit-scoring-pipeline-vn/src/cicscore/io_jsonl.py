"""JSONL codec for borrowers + feature vectors + scores."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from cicscore.cic_groups import CICGroup
from cicscore.schema import (
    Borrower,
    ContractType,
    CreditContract,
    GroupAssessment,
    Inquiry,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from cicscore.features import FeatureVector
    from cicscore.scoring import Score


# ---------------------------------------------------------------------------
# Type-checked decoder helpers.


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


def _optional_int(d: dict[str, object], key: str) -> int | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int or null, got {type(v).__name__}")
    return v


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def _require_date(d: dict[str, object], key: str) -> date:
    return date.fromisoformat(_require_str(d, key))


def _optional_date(d: dict[str, object], key: str) -> date | None:
    s = _optional_str(d, key)
    return None if s is None else date.fromisoformat(s)


# ---------------------------------------------------------------------------
# Borrower encode / decode.


def contract_to_dict(c: CreditContract) -> dict[str, object]:
    return {
        "contract_id": c.contract_id,
        "borrower_id": c.borrower_id,
        "lender_bank": c.lender_bank,
        "contract_type": c.contract_type.value,
        "original_amount_vnd": c.original_amount_vnd,
        "opened_at": c.opened_at.isoformat(),
        "closed_at": None if c.closed_at is None else c.closed_at.isoformat(),
    }


def contract_from_dict(d: dict[str, object]) -> CreditContract:
    return CreditContract(
        contract_id=_require_str(d, "contract_id"),
        borrower_id=_require_str(d, "borrower_id"),
        lender_bank=_require_str(d, "lender_bank"),
        contract_type=ContractType(_require_str(d, "contract_type")),
        original_amount_vnd=_require_int(d, "original_amount_vnd"),
        opened_at=_require_date(d, "opened_at"),
        closed_at=_optional_date(d, "closed_at"),
    )


def assessment_to_dict(a: GroupAssessment) -> dict[str, object]:
    return {
        "contract_id": a.contract_id,
        "as_of_month": a.as_of_month.isoformat(),
        "group": int(a.group),
        "outstanding_principal_vnd": a.outstanding_principal_vnd,
        "outstanding_interest_vnd": a.outstanding_interest_vnd,
        "days_past_due": a.days_past_due,
    }


def assessment_from_dict(d: dict[str, object]) -> GroupAssessment:
    return GroupAssessment(
        contract_id=_require_str(d, "contract_id"),
        as_of_month=_require_date(d, "as_of_month"),
        group=CICGroup(_require_int(d, "group")),
        outstanding_principal_vnd=_require_int(d, "outstanding_principal_vnd"),
        outstanding_interest_vnd=_require_int(d, "outstanding_interest_vnd"),
        days_past_due=_require_int(d, "days_past_due"),
    )


def inquiry_to_dict(q: Inquiry) -> dict[str, object]:
    return {
        "borrower_id": q.borrower_id,
        "lender_bank": q.lender_bank,
        "inquired_at": q.inquired_at.isoformat(),
        "purpose": q.purpose,
    }


def inquiry_from_dict(d: dict[str, object]) -> Inquiry:
    return Inquiry(
        borrower_id=_require_str(d, "borrower_id"),
        lender_bank=_require_str(d, "lender_bank"),
        inquired_at=_require_date(d, "inquired_at"),
        purpose=_require_str(d, "purpose"),
    )


def borrower_to_dict(b: Borrower) -> dict[str, object]:
    return {
        "borrower_id": b.borrower_id,
        "monthly_income_vnd": b.monthly_income_vnd,
        "contracts": [contract_to_dict(c) for c in b.contracts],
        "assessments": [assessment_to_dict(a) for a in b.assessments],
        "inquiries": [inquiry_to_dict(q) for q in b.inquiries],
    }


def borrower_from_dict(d: dict[str, object]) -> Borrower:
    contracts_raw = d.get("contracts", [])
    assessments_raw = d.get("assessments", [])
    inquiries_raw = d.get("inquiries", [])
    if not isinstance(contracts_raw, list):
        raise TypeError("contracts must be a list")
    if not isinstance(assessments_raw, list):
        raise TypeError("assessments must be a list")
    if not isinstance(inquiries_raw, list):
        raise TypeError("inquiries must be a list")
    contracts = tuple(contract_from_dict(c) for c in contracts_raw if isinstance(c, dict))
    assessments = tuple(assessment_from_dict(a) for a in assessments_raw if isinstance(a, dict))
    inquiries = tuple(inquiry_from_dict(q) for q in inquiries_raw if isinstance(q, dict))
    return Borrower(
        borrower_id=_require_str(d, "borrower_id"),
        contracts=contracts,
        assessments=assessments,
        inquiries=inquiries,
        monthly_income_vnd=_optional_int(d, "monthly_income_vnd"),
    )


def dump_borrowers(borrowers: Iterable[Borrower]) -> str:
    return "\n".join(json.dumps(borrower_to_dict(b), ensure_ascii=False) for b in borrowers) + "\n"


def load_borrowers(text: str) -> Iterator[Borrower]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield borrower_from_dict(json.loads(line))


# ---------------------------------------------------------------------------
# FeatureVector / Score encode / decode.


def feature_to_dict(f: FeatureVector) -> dict[str, object]:
    return {
        "borrower_id": f.borrower_id,
        "observation_date": f.observation_date.isoformat(),
        "current_max_group": None if f.current_max_group is None else int(f.current_max_group),
        "worst_group_ever": None if f.worst_group_ever is None else int(f.worst_group_ever),
        "max_group_24m": None if f.max_group_24m is None else int(f.max_group_24m),
        "months_in_group_2plus_24m": f.months_in_group_2plus_24m,
        "active_contracts": f.active_contracts,
        "unique_lenders": f.unique_lenders,
        "total_outstanding_principal_vnd": f.total_outstanding_principal_vnd,
        "total_outstanding_interest_vnd": f.total_outstanding_interest_vnd,
        "provision_estimate_vnd": f.provision_estimate_vnd,
        "months_since_first_credit": f.months_since_first_credit,
        "months_since_last_credit_open": f.months_since_last_credit_open,
        "inquiries_3m": f.inquiries_3m,
        "inquiries_6m": f.inquiries_6m,
        "inquiries_12m": f.inquiries_12m,
        "days_since_last_inquiry": f.days_since_last_inquiry,
        "has_term_loan": f.has_term_loan,
        "has_mortgage": f.has_mortgage,
        "has_auto_loan": f.has_auto_loan,
        "has_credit_card": f.has_credit_card,
        "has_overdraft": f.has_overdraft,
        "has_business_loan": f.has_business_loan,
        "dti_ratio": f.dti_ratio,
    }


def score_to_dict(s: Score) -> dict[str, object]:
    return {
        "borrower_id": s.borrower_id,
        "score": s.score,
        "reasons": [{"label": r.label, "delta": r.delta} for r in s.reasons],
    }


def dump_features(features: Iterable[FeatureVector]) -> str:
    return "\n".join(json.dumps(feature_to_dict(f), ensure_ascii=False) for f in features) + "\n"


def dump_scores(scores: Iterable[Score]) -> str:
    return "\n".join(json.dumps(score_to_dict(s), ensure_ascii=False) for s in scores) + "\n"


__all__ = [
    "assessment_from_dict",
    "assessment_to_dict",
    "borrower_from_dict",
    "borrower_to_dict",
    "contract_from_dict",
    "contract_to_dict",
    "dump_borrowers",
    "dump_features",
    "dump_scores",
    "feature_to_dict",
    "inquiry_from_dict",
    "inquiry_to_dict",
    "load_borrowers",
    "score_to_dict",
]
