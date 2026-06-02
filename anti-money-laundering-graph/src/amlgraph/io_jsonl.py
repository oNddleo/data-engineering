"""JSONL codec for accounts, transactions, and alerts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from amlgraph.alerts import AlertKind, AMLAlert, Severity
from amlgraph.schema import Account, AccountType, Channel, RiskFlag, Transaction

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


def account_to_dict(a: Account) -> dict[str, object]:
    return {
        "account_id": a.account_id,
        "bank_bin": a.bank_bin,
        "account_type": a.account_type.value,
        "risk_flags": [f.value for f in a.risk_flags],
    }


def account_from_dict(d: dict[str, object]) -> Account:
    flags_raw = d.get("risk_flags", [])
    if not isinstance(flags_raw, list):
        raise TypeError("risk_flags must be a list")
    return Account(
        account_id=_require_str(d, "account_id"),
        bank_bin=_require_str(d, "bank_bin"),
        account_type=AccountType(_require_str(d, "account_type")),
        risk_flags=tuple(RiskFlag(str(f)) for f in flags_raw),
    )


def txn_to_dict(t: Transaction) -> dict[str, object]:
    return {
        "txn_id": t.txn_id,
        "from_account": t.from_account,
        "to_account": t.to_account,
        "amount_vnd": t.amount_vnd,
        "occurred_at": t.occurred_at.isoformat(),
        "channel": t.channel.value,
    }


def txn_from_dict(d: dict[str, object]) -> Transaction:
    return Transaction(
        txn_id=_require_str(d, "txn_id"),
        from_account=_require_str(d, "from_account"),
        to_account=_require_str(d, "to_account"),
        amount_vnd=_require_int(d, "amount_vnd"),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        channel=Channel(_require_str(d, "channel")),
    )


def alert_to_dict(a: AMLAlert) -> dict[str, object]:
    return {
        "kind": a.kind.value,
        "severity": a.severity.value,
        "primary_account": a.primary_account,
        "related_accounts": list(a.related_accounts),
        "total_amount_vnd": a.total_amount_vnd,
        "detail": a.detail,
        "txn_ids": list(a.txn_ids),
    }


def alert_from_dict(d: dict[str, object]) -> AMLAlert:
    rel = d.get("related_accounts", [])
    txns = d.get("txn_ids", [])
    if not isinstance(rel, list) or not isinstance(txns, list):
        raise TypeError("related_accounts and txn_ids must be lists")
    return AMLAlert(
        kind=AlertKind(_require_str(d, "kind")),
        severity=Severity(_require_str(d, "severity")),
        primary_account=_require_str(d, "primary_account"),
        related_accounts=tuple(str(x) for x in rel),
        total_amount_vnd=_require_int(d, "total_amount_vnd"),
        detail=_require_str(d, "detail"),
        txn_ids=tuple(str(x) for x in txns),
    )


def dump_accounts(accounts: Iterable[Account]) -> str:
    return "\n".join(json.dumps(account_to_dict(a), ensure_ascii=False) for a in accounts) + "\n"


def load_accounts(text: str) -> Iterator[Account]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield account_from_dict(json.loads(line))


def dump_txns(txns: Iterable[Transaction]) -> str:
    return "\n".join(json.dumps(txn_to_dict(t), ensure_ascii=False) for t in txns) + "\n"


def load_txns(text: str) -> Iterator[Transaction]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield txn_from_dict(json.loads(line))


def dump_alerts(alerts: Iterable[AMLAlert]) -> str:
    return "\n".join(json.dumps(alert_to_dict(a), ensure_ascii=False) for a in alerts) + "\n"


def load_alerts(text: str) -> Iterator[AMLAlert]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield alert_from_dict(json.loads(line))


__all__ = [
    "account_from_dict",
    "account_to_dict",
    "alert_from_dict",
    "alert_to_dict",
    "dump_accounts",
    "dump_alerts",
    "dump_txns",
    "load_accounts",
    "load_alerts",
    "load_txns",
    "txn_from_dict",
    "txn_to_dict",
]
