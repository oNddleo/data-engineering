"""healthcare-claims-processor — VN BHYT social-insurance claims pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from bhyt.calculator import calculate
    from bhyt.card import PrefixInfo, decode_prefix, is_valid_format, normalise
    from bhyt.coverage import (
        base_rate_bps,
        effective_rate_bps,
        referral_penalty_bps,
    )
    from bhyt.icd10vn import ICDEntry, bundled_codes, codes_by_chapter, lookup
    from bhyt.io_jsonl import (
        card_from_dict,
        card_to_dict,
        claim_from_dict,
        claim_to_dict,
        dump_cards,
        dump_claims,
        dump_patients,
        dump_reimbursements,
        load_cards,
        load_claims,
        load_patients,
        load_reimbursements,
        patient_from_dict,
        patient_to_dict,
        reimb_from_dict,
        reimb_to_dict,
    )
    from bhyt.schema import (
        VN_TZ,
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
    from bhyt.simulator import generate


_LAZY: dict[str, tuple[str, str]] = {
    "BHYTCard": ("bhyt.schema", "BHYTCard"),
    "CareLevel": ("bhyt.schema", "CareLevel"),
    "Claim": ("bhyt.schema", "Claim"),
    "ClaimItem": ("bhyt.schema", "ClaimItem"),
    "Diagnosis": ("bhyt.schema", "Diagnosis"),
    "ExemptionCategory": ("bhyt.schema", "ExemptionCategory"),
    "ICDEntry": ("bhyt.icd10vn", "ICDEntry"),
    "Patient": ("bhyt.schema", "Patient"),
    "PrefixInfo": ("bhyt.card", "PrefixInfo"),
    "Reimbursement": ("bhyt.schema", "Reimbursement"),
    "ServiceKind": ("bhyt.schema", "ServiceKind"),
    "VN_TZ": ("bhyt.schema", "VN_TZ"),
    "base_rate_bps": ("bhyt.coverage", "base_rate_bps"),
    "bundled_codes": ("bhyt.icd10vn", "bundled_codes"),
    "calculate": ("bhyt.calculator", "calculate"),
    "card_from_dict": ("bhyt.io_jsonl", "card_from_dict"),
    "card_to_dict": ("bhyt.io_jsonl", "card_to_dict"),
    "claim_from_dict": ("bhyt.io_jsonl", "claim_from_dict"),
    "claim_to_dict": ("bhyt.io_jsonl", "claim_to_dict"),
    "codes_by_chapter": ("bhyt.icd10vn", "codes_by_chapter"),
    "decode_prefix": ("bhyt.card", "decode_prefix"),
    "dump_cards": ("bhyt.io_jsonl", "dump_cards"),
    "dump_claims": ("bhyt.io_jsonl", "dump_claims"),
    "dump_patients": ("bhyt.io_jsonl", "dump_patients"),
    "dump_reimbursements": ("bhyt.io_jsonl", "dump_reimbursements"),
    "effective_rate_bps": ("bhyt.coverage", "effective_rate_bps"),
    "generate": ("bhyt.simulator", "generate"),
    "is_valid_format": ("bhyt.card", "is_valid_format"),
    "load_cards": ("bhyt.io_jsonl", "load_cards"),
    "load_claims": ("bhyt.io_jsonl", "load_claims"),
    "load_patients": ("bhyt.io_jsonl", "load_patients"),
    "load_reimbursements": ("bhyt.io_jsonl", "load_reimbursements"),
    "lookup": ("bhyt.icd10vn", "lookup"),
    "normalise": ("bhyt.card", "normalise"),
    "patient_from_dict": ("bhyt.io_jsonl", "patient_from_dict"),
    "patient_to_dict": ("bhyt.io_jsonl", "patient_to_dict"),
    "referral_penalty_bps": ("bhyt.coverage", "referral_penalty_bps"),
    "reimb_from_dict": ("bhyt.io_jsonl", "reimb_from_dict"),
    "reimb_to_dict": ("bhyt.io_jsonl", "reimb_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BHYTCard",
    "CareLevel",
    "Claim",
    "ClaimItem",
    "Diagnosis",
    "ExemptionCategory",
    "ICDEntry",
    "Patient",
    "PrefixInfo",
    "Reimbursement",
    "ServiceKind",
    "VN_TZ",
    "__version__",
    "base_rate_bps",
    "bundled_codes",
    "calculate",
    "card_from_dict",
    "card_to_dict",
    "claim_from_dict",
    "claim_to_dict",
    "codes_by_chapter",
    "decode_prefix",
    "dump_cards",
    "dump_claims",
    "dump_patients",
    "dump_reimbursements",
    "effective_rate_bps",
    "generate",
    "is_valid_format",
    "load_cards",
    "load_claims",
    "load_patients",
    "load_reimbursements",
    "lookup",
    "normalise",
    "patient_from_dict",
    "patient_to_dict",
    "referral_penalty_bps",
    "reimb_from_dict",
    "reimb_to_dict",
]
