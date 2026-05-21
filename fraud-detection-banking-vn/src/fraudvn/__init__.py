"""fraud-detection-banking-vn — real-time fraud engine for VN internet banking."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "AccountState": ("fraudvn.state", "AccountState"),
        "BLOCK_THRESHOLD": ("fraudvn.engine", "BLOCK_THRESHOLD"),
        "Channel": ("fraudvn.schema", "Channel"),
        "Decision": ("fraudvn.schema", "Decision"),
        "FraudDecision": ("fraudvn.schema", "FraudDecision"),
        "FraudEngine": ("fraudvn.engine", "FraudEngine"),
        "KEYWORD_CATEGORY_WEIGHTS": ("fraudvn.keywords", "KEYWORD_CATEGORY_WEIGHTS"),
        "REVIEW_THRESHOLD": ("fraudvn.engine", "REVIEW_THRESHOLD"),
        "SCAM_KEYWORDS": ("fraudvn.keywords", "SCAM_KEYWORDS"),
        "SignalHit": ("fraudvn.schema", "SignalHit"),
        "StateStore": ("fraudvn.state", "StateStore"),
        "TransactionRequest": ("fraudvn.schema", "TransactionRequest"),
        "VN_TZ": ("fraudvn.schema", "VN_TZ"),
        "decision_from_dict": ("fraudvn.io_jsonl", "decision_from_dict"),
        "decision_to_dict": ("fraudvn.io_jsonl", "decision_to_dict"),
        "dump_decisions": ("fraudvn.io_jsonl", "dump_decisions"),
        "dump_requests": ("fraudvn.io_jsonl", "dump_requests"),
        "find_scam_keywords": ("fraudvn.keywords", "find_scam_keywords"),
        "generate": ("fraudvn.simulator", "generate"),
        "load_decisions": ("fraudvn.io_jsonl", "load_decisions"),
        "load_requests": ("fraudvn.io_jsonl", "load_requests"),
        "normalize_vn_text": ("fraudvn.keywords", "normalize_vn_text"),
        "req_from_dict": ("fraudvn.io_jsonl", "req_from_dict"),
        "req_to_dict": ("fraudvn.io_jsonl", "req_to_dict"),
        "score_to_decision": ("fraudvn.engine", "score_to_decision"),
        "signal_beneficiary_hot": ("fraudvn.signals", "signal_beneficiary_hot"),
        "signal_blacklist_beneficiary": ("fraudvn.signals", "signal_blacklist_beneficiary"),
        "signal_keyword": ("fraudvn.signals", "signal_keyword"),
        "signal_new_beneficiary_large": ("fraudvn.signals", "signal_new_beneficiary_large"),
        "signal_night_transfer": ("fraudvn.signals", "signal_night_transfer"),
        "signal_otp_race": ("fraudvn.signals", "signal_otp_race"),
        "signal_round_amount_below": ("fraudvn.signals", "signal_round_amount_below"),
        "signal_velocity_burst": ("fraudvn.signals", "signal_velocity_burst"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BLOCK_THRESHOLD",
    "KEYWORD_CATEGORY_WEIGHTS",
    "REVIEW_THRESHOLD",
    "SCAM_KEYWORDS",
    "VN_TZ",
    "AccountState",
    "Channel",
    "Decision",
    "FraudDecision",
    "FraudEngine",
    "SignalHit",
    "StateStore",
    "TransactionRequest",
    "__version__",
    "decision_from_dict",
    "decision_to_dict",
    "dump_decisions",
    "dump_requests",
    "find_scam_keywords",
    "generate",
    "load_decisions",
    "load_requests",
    "normalize_vn_text",
    "req_from_dict",
    "req_to_dict",
    "score_to_decision",
    "signal_beneficiary_hot",
    "signal_blacklist_beneficiary",
    "signal_keyword",
    "signal_new_beneficiary_large",
    "signal_night_transfer",
    "signal_otp_race",
    "signal_round_amount_below",
    "signal_velocity_burst",
]
