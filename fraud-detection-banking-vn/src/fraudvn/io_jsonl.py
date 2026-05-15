"""JSONL codec for transaction requests + fraud decisions."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from fraudvn.schema import (
    Channel,
    Decision,
    FraudDecision,
    SignalHit,
    TransactionRequest,
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


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def req_to_dict(r: TransactionRequest) -> dict[str, object]:
    return {
        "txn_id": r.txn_id,
        "initiator_account": r.initiator_account,
        "beneficiary_account": r.beneficiary_account,
        "beneficiary_bank_bin": r.beneficiary_bank_bin,
        "amount_vnd": r.amount_vnd,
        "narrative": r.narrative,
        "channel": r.channel.value,
        "occurred_at": r.occurred_at.isoformat(),
        "otp_issued_at": None if r.otp_issued_at is None else r.otp_issued_at.isoformat(),
        "otp_verified_at": None if r.otp_verified_at is None else r.otp_verified_at.isoformat(),
    }


def req_from_dict(d: dict[str, object]) -> TransactionRequest:
    otp_iss = _optional_str(d, "otp_issued_at")
    otp_ver = _optional_str(d, "otp_verified_at")
    return TransactionRequest(
        txn_id=_require_str(d, "txn_id"),
        initiator_account=_require_str(d, "initiator_account"),
        beneficiary_account=_require_str(d, "beneficiary_account"),
        beneficiary_bank_bin=_require_str(d, "beneficiary_bank_bin"),
        amount_vnd=_require_int(d, "amount_vnd"),
        narrative=_require_str(d, "narrative"),
        channel=Channel(_require_str(d, "channel")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        otp_issued_at=None if otp_iss is None else datetime.fromisoformat(otp_iss),
        otp_verified_at=None if otp_ver is None else datetime.fromisoformat(otp_ver),
    )


def decision_to_dict(d: FraudDecision) -> dict[str, object]:
    return {
        "txn_id": d.txn_id,
        "decision": d.decision.value,
        "score": d.score,
        "signals": [{"name": s.name, "points": s.points, "detail": s.detail} for s in d.signals],
        "latency_ms": d.latency_ms,
    }


def decision_from_dict(d: dict[str, object]) -> FraudDecision:
    signals_raw = d.get("signals", [])
    if not isinstance(signals_raw, list):
        raise TypeError("signals must be a list")
    signals: list[SignalHit] = []
    for entry in signals_raw:
        if not isinstance(entry, dict):
            continue
        signals.append(
            SignalHit(
                name=_require_str(entry, "name"),
                points=_require_int(entry, "points"),
                detail=_require_str(entry, "detail"),
            )
        )
    latency_raw = d.get("latency_ms", 0.0)
    if isinstance(latency_raw, bool) or not isinstance(latency_raw, int | float):
        raise TypeError("latency_ms must be a number")
    return FraudDecision(
        txn_id=_require_str(d, "txn_id"),
        decision=Decision(_require_str(d, "decision")),
        score=_require_int(d, "score"),
        signals=tuple(signals),
        latency_ms=float(latency_raw),
    )


def dump_requests(reqs: Iterable[TransactionRequest]) -> str:
    return "\n".join(json.dumps(req_to_dict(r), ensure_ascii=False) for r in reqs) + "\n"


def load_requests(text: str) -> Iterator[TransactionRequest]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield req_from_dict(json.loads(line))


def dump_decisions(decisions: Iterable[FraudDecision]) -> str:
    return "\n".join(json.dumps(decision_to_dict(d), ensure_ascii=False) for d in decisions) + "\n"


def load_decisions(text: str) -> Iterator[FraudDecision]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield decision_from_dict(json.loads(line))


__all__ = [
    "decision_from_dict",
    "decision_to_dict",
    "dump_decisions",
    "dump_requests",
    "load_decisions",
    "load_requests",
    "req_from_dict",
    "req_to_dict",
]
