"""credit-scoring-pipeline-vn — CIC feature engineering + baseline scoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from cicscore.cic_groups import (
        PROVISION_RATE,
        VN_NAMES,
        CICGroup,
        group_from_days_past_due,
        provision_amount_vnd,
    )
    from cicscore.features import FeatureVector, extract
    from cicscore.io_jsonl import (
        borrower_from_dict,
        borrower_to_dict,
        dump_borrowers,
        dump_features,
        dump_scores,
        load_borrowers,
    )
    from cicscore.schema import (
        Borrower,
        ContractType,
        CreditContract,
        GroupAssessment,
        Inquiry,
        add_months,
        first_of_month,
        months_between,
    )
    from cicscore.scoring import (
        BASE_SCORE,
        MAX_SCORE,
        MIN_SCORE,
        Score,
        ScoreReason,
        baseline_score,
    )
    from cicscore.simulator import RISK_PROFILES, generate, generate_borrower


_LAZY: dict[str, tuple[str, str]] = {
    "BASE_SCORE": ("cicscore.scoring", "BASE_SCORE"),
    "Borrower": ("cicscore.schema", "Borrower"),
    "CICGroup": ("cicscore.cic_groups", "CICGroup"),
    "ContractType": ("cicscore.schema", "ContractType"),
    "CreditContract": ("cicscore.schema", "CreditContract"),
    "FeatureVector": ("cicscore.features", "FeatureVector"),
    "GroupAssessment": ("cicscore.schema", "GroupAssessment"),
    "Inquiry": ("cicscore.schema", "Inquiry"),
    "MAX_SCORE": ("cicscore.scoring", "MAX_SCORE"),
    "MIN_SCORE": ("cicscore.scoring", "MIN_SCORE"),
    "PROVISION_RATE": ("cicscore.cic_groups", "PROVISION_RATE"),
    "RISK_PROFILES": ("cicscore.simulator", "RISK_PROFILES"),
    "Score": ("cicscore.scoring", "Score"),
    "ScoreReason": ("cicscore.scoring", "ScoreReason"),
    "VN_NAMES": ("cicscore.cic_groups", "VN_NAMES"),
    "add_months": ("cicscore.schema", "add_months"),
    "baseline_score": ("cicscore.scoring", "baseline_score"),
    "borrower_from_dict": ("cicscore.io_jsonl", "borrower_from_dict"),
    "borrower_to_dict": ("cicscore.io_jsonl", "borrower_to_dict"),
    "dump_borrowers": ("cicscore.io_jsonl", "dump_borrowers"),
    "dump_features": ("cicscore.io_jsonl", "dump_features"),
    "dump_scores": ("cicscore.io_jsonl", "dump_scores"),
    "extract": ("cicscore.features", "extract"),
    "first_of_month": ("cicscore.schema", "first_of_month"),
    "generate": ("cicscore.simulator", "generate"),
    "generate_borrower": ("cicscore.simulator", "generate_borrower"),
    "group_from_days_past_due": ("cicscore.cic_groups", "group_from_days_past_due"),
    "load_borrowers": ("cicscore.io_jsonl", "load_borrowers"),
    "months_between": ("cicscore.schema", "months_between"),
    "provision_amount_vnd": ("cicscore.cic_groups", "provision_amount_vnd"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BASE_SCORE",
    "MAX_SCORE",
    "MIN_SCORE",
    "PROVISION_RATE",
    "RISK_PROFILES",
    "VN_NAMES",
    "Borrower",
    "CICGroup",
    "ContractType",
    "CreditContract",
    "FeatureVector",
    "GroupAssessment",
    "Inquiry",
    "Score",
    "ScoreReason",
    "__version__",
    "add_months",
    "baseline_score",
    "borrower_from_dict",
    "borrower_to_dict",
    "dump_borrowers",
    "dump_features",
    "dump_scores",
    "extract",
    "first_of_month",
    "generate",
    "generate_borrower",
    "group_from_days_past_due",
    "load_borrowers",
    "months_between",
    "provision_amount_vnd",
]
