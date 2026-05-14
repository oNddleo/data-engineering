"""JSONL codec for TransactionEvents (input) + persisted ledgers (state)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from sbv2345.ledger import AuditLedger, SealedAuditRecord, _compute_record_hash
from sbv2345.schema import (
    AuditEvent,
    AuthMethod,
    BiometricMethod,
    Channel,
    TransactionEvent,
    TriggerKind,
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


# ---------------------------------------------------------------------------
# TransactionEvent.


def txn_to_dict(t: TransactionEvent) -> dict[str, object]:
    return {
        "txn_id": t.txn_id,
        "initiator_account": t.initiator_account,
        "beneficiary_account": t.beneficiary_account,
        "amount_vnd": t.amount_vnd,
        "channel": t.channel.value,
        "occurred_at": t.occurred_at.isoformat(),
        "auth_method": t.auth_method.value,
        "biometric_method": None if t.biometric_method is None else t.biometric_method.value,
        "cross_border": t.cross_border,
        "initiator_bank_bin": t.initiator_bank_bin,
        "beneficiary_bank_bin": t.beneficiary_bank_bin,
    }


def txn_from_dict(d: dict[str, object]) -> TransactionEvent:
    bio_raw = _optional_str(d, "biometric_method")
    return TransactionEvent(
        txn_id=_require_str(d, "txn_id"),
        initiator_account=_require_str(d, "initiator_account"),
        beneficiary_account=_require_str(d, "beneficiary_account"),
        amount_vnd=_require_int(d, "amount_vnd"),
        channel=Channel(_require_str(d, "channel")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        auth_method=AuthMethod(_require_str(d, "auth_method")),
        biometric_method=None if bio_raw is None else BiometricMethod(bio_raw),
        cross_border=bool(d.get("cross_border", False)),
        initiator_bank_bin=str(d.get("initiator_bank_bin", "")),
        beneficiary_bank_bin=str(d.get("beneficiary_bank_bin", "")),
    )


def dump_txns(txns: Iterable[TransactionEvent]) -> str:
    return "\n".join(json.dumps(txn_to_dict(t), ensure_ascii=False) for t in txns) + "\n"


def load_txns(text: str) -> Iterator[TransactionEvent]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield txn_from_dict(json.loads(line))


# ---------------------------------------------------------------------------
# Ledger.


def record_to_dict(r: SealedAuditRecord) -> dict[str, object]:
    return {
        "sequence_number": r.sequence_number,
        "prev_hash": r.prev_hash,
        "txn": txn_to_dict(r.event.txn),
        "triggered_kinds": [k.value for k in r.event.triggered_kinds],
        "legal_bases": list(r.event.legal_bases),
        "daily_cumulative_after_vnd": r.event.daily_cumulative_after_vnd,
        "sealed_at": r.sealed_at.isoformat(),
        "record_hash": r.record_hash,
    }


def record_from_dict(d: dict[str, object]) -> SealedAuditRecord:
    txn_raw = d["txn"]
    if not isinstance(txn_raw, dict):
        raise TypeError("txn must be an object")
    triggers_raw = d.get("triggered_kinds", [])
    if not isinstance(triggers_raw, list):
        raise TypeError("triggered_kinds must be a list")
    bases_raw = d.get("legal_bases", [])
    if not isinstance(bases_raw, list):
        raise TypeError("legal_bases must be a list")
    event = AuditEvent(
        txn=txn_from_dict(txn_raw),
        triggered_kinds=tuple(TriggerKind(str(k)) for k in triggers_raw),
        legal_bases=tuple(str(b) for b in bases_raw),
        daily_cumulative_after_vnd=_require_int(d, "daily_cumulative_after_vnd"),
    )
    return SealedAuditRecord(
        sequence_number=_require_int(d, "sequence_number"),
        prev_hash=_require_str(d, "prev_hash"),
        event=event,
        sealed_at=datetime.fromisoformat(_require_str(d, "sealed_at")),
        record_hash=_require_str(d, "record_hash"),
    )


def dump_ledger(ledger: AuditLedger) -> str:
    return "\n".join(json.dumps(record_to_dict(r), ensure_ascii=False) for r in ledger) + "\n"


def load_ledger(text: str) -> AuditLedger:
    """Rehydrate a ledger from JSONL.

    Re-runs the chain verification on the loaded records by appending
    via :class:`AuditLedger.append` *would re-hash* them — but that
    would overwrite ``record_hash`` with a freshly-computed value
    that hides any on-disk tampering. Instead we build the in-memory
    list directly and then call :meth:`AuditLedger.verify` so a
    bad-on-disk record raises :class:`TamperDetected` at load time.
    """
    ledger = AuditLedger()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = record_from_dict(json.loads(line))
        ledger._records.append(rec)
    ledger.verify()
    return ledger


# ---------------------------------------------------------------------------
# Sanity-check helpers used in tests.

__all__ = [
    "_compute_record_hash",
    "dump_ledger",
    "dump_txns",
    "load_ledger",
    "load_txns",
    "record_from_dict",
    "record_to_dict",
    "txn_from_dict",
    "txn_to_dict",
]
