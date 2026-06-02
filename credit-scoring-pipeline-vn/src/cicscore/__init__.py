"""credit-scoring-pipeline-vn — CIC feature engineering + baseline scoring."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
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
