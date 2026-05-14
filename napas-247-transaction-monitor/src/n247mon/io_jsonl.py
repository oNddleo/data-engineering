"""JSON-Lines codec for transactions and alerts.

We pick JSONL (one JSON object per newline-delimited line) instead
of a single big JSON array because it's:

* Friendly to streaming both directions — every line is a complete
  record that can be flushed to disk or piped through Kafka.
* `jq`-able, `grep`-able, `head`-able. Ops loves this.
* Round-trippable without buffering the whole file in memory.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from n247mon.alerts import Alert, AlertKind, Severity
from n247mon.schema import Channel, Transaction

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def txn_to_dict(t: Transaction) -> dict[str, object]:
    return {
        "txn_id": t.txn_id,
        "initiator_account": t.initiator_account,
        "initiator_bank_bin": t.initiator_bank_bin,
        "beneficiary_account": t.beneficiary_account,
        "beneficiary_bank_bin": t.beneficiary_bank_bin,
        "amount_vnd": t.amount_vnd,
        "channel": t.channel.value,
        "occurred_at": t.occurred_at.isoformat(),
        "biometric_verified": t.biometric_verified,
        "device_id": t.device_id,
        "geo_ip": t.geo_ip,
    }


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def txn_from_dict(d: dict[str, object]) -> Transaction:
    return Transaction(
        txn_id=_require_str(d, "txn_id"),
        initiator_account=_require_str(d, "initiator_account"),
        initiator_bank_bin=_require_str(d, "initiator_bank_bin"),
        beneficiary_account=_require_str(d, "beneficiary_account"),
        beneficiary_bank_bin=_require_str(d, "beneficiary_bank_bin"),
        amount_vnd=_require_int(d, "amount_vnd"),
        channel=Channel(_require_str(d, "channel")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        biometric_verified=bool(d["biometric_verified"]),
        device_id=_optional_str(d, "device_id"),
        geo_ip=_optional_str(d, "geo_ip"),
    )


def alert_to_dict(a: Alert) -> dict[str, object]:
    return {
        "kind": a.kind.value,
        "severity": a.severity.value,
        "txn_id": a.txn_id,
        "account": a.account,
        "detail": a.detail,
        "amount_vnd": a.amount_vnd,
    }


def alert_from_dict(d: dict[str, object]) -> Alert:
    return Alert(
        kind=AlertKind(_require_str(d, "kind")),
        severity=Severity(_require_str(d, "severity")),
        txn_id=_require_str(d, "txn_id"),
        account=_require_str(d, "account"),
        detail=_require_str(d, "detail"),
        amount_vnd=_require_int(d, "amount_vnd"),
    )


def dump_txns(txns: Iterable[Transaction]) -> str:
    return "\n".join(json.dumps(txn_to_dict(t), ensure_ascii=False) for t in txns) + "\n"


def load_txns(text: str) -> Iterator[Transaction]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield txn_from_dict(json.loads(line))


def dump_alerts(alerts: Iterable[Alert]) -> str:
    return "\n".join(json.dumps(alert_to_dict(a), ensure_ascii=False) for a in alerts) + "\n"


def load_alerts(text: str) -> Iterator[Alert]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield alert_from_dict(json.loads(line))


__all__ = [
    "alert_from_dict",
    "alert_to_dict",
    "dump_alerts",
    "dump_txns",
    "load_alerts",
    "load_txns",
    "txn_from_dict",
    "txn_to_dict",
]
