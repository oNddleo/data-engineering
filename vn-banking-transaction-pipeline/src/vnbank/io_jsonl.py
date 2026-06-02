"""JSONL codec for Transaction / DailySummary / AMLFinding."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vnbank.aml import AMLFinding, AMLKind
from vnbank.schema import (
    DailySummary,
    Transaction,
    TxnDirection,
    TxnKind,
    TxnStatus,
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


def _opt_str(d: dict[str, object], key: str) -> str:
    v = d.get(key, "")
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


# ---------- Transaction -----------------------------------------------------


def txn_to_dict(t: Transaction) -> dict[str, object]:
    return {
        "txn_id": t.txn_id,
        "account_number": t.account_number,
        "bank_bin": t.bank_bin,
        "kind": t.kind.value,
        "direction": t.direction.value,
        "amount_vnd": t.amount_vnd,
        "occurred_at": t.occurred_at.isoformat(),
        "status": t.status.value,
        "counterparty_account": t.counterparty_account,
        "counterparty_bank_bin": t.counterparty_bank_bin,
        "description": t.description,
    }


def txn_from_dict(d: dict[str, object]) -> Transaction:
    return Transaction(
        txn_id=_require_str(d, "txn_id"),
        account_number=_require_str(d, "account_number"),
        bank_bin=_require_str(d, "bank_bin"),
        kind=TxnKind(_require_str(d, "kind")),
        direction=TxnDirection(_require_str(d, "direction")),
        amount_vnd=_require_int(d, "amount_vnd"),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        status=TxnStatus(_opt_str(d, "status") or TxnStatus.POSTED.value),
        counterparty_account=_opt_str(d, "counterparty_account"),
        counterparty_bank_bin=_opt_str(d, "counterparty_bank_bin"),
        description=_opt_str(d, "description"),
    )


# ---------- DailySummary ----------------------------------------------------


def summary_to_dict(s: DailySummary) -> dict[str, object]:
    return {
        "account_number": s.account_number,
        "bank_bin": s.bank_bin,
        "date": s.date,
        "n_txns": s.n_txns,
        "total_debit_vnd": s.total_debit_vnd,
        "total_credit_vnd": s.total_credit_vnd,
        "n_cash_deposits": s.n_cash_deposits,
        "cash_deposit_amount_vnd": s.cash_deposit_amount_vnd,
        "n_cash_withdrawals": s.n_cash_withdrawals,
        "cash_withdrawal_amount_vnd": s.cash_withdrawal_amount_vnd,
    }


def summary_from_dict(d: dict[str, object]) -> DailySummary:
    return DailySummary(
        account_number=_require_str(d, "account_number"),
        bank_bin=_require_str(d, "bank_bin"),
        date=_require_str(d, "date"),
        n_txns=_require_int(d, "n_txns"),
        total_debit_vnd=_require_int(d, "total_debit_vnd"),
        total_credit_vnd=_require_int(d, "total_credit_vnd"),
        n_cash_deposits=_require_int(d, "n_cash_deposits"),
        cash_deposit_amount_vnd=_require_int(d, "cash_deposit_amount_vnd"),
        n_cash_withdrawals=_require_int(d, "n_cash_withdrawals"),
        cash_withdrawal_amount_vnd=_require_int(d, "cash_withdrawal_amount_vnd"),
    )


# ---------- AMLFinding ------------------------------------------------------


def aml_to_dict(f: AMLFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "account_number": f.account_number,
        "bank_bin": f.bank_bin,
        "detail": f.detail,
        "metric": f.metric,
    }


def aml_from_dict(d: dict[str, object]) -> AMLFinding:
    return AMLFinding(
        kind=AMLKind(_require_str(d, "kind")),
        account_number=_require_str(d, "account_number"),
        bank_bin=_require_str(d, "bank_bin"),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_txns(items: Iterable[Transaction]) -> str:
    return _dump(txn_to_dict(t) for t in items)


def dump_summaries(items: Iterable[DailySummary]) -> str:
    return _dump(summary_to_dict(s) for s in items)


def dump_amls(items: Iterable[AMLFinding]) -> str:
    return _dump(aml_to_dict(f) for f in items)


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


def load_txns(text: str) -> list[Transaction]:
    return [txn_from_dict(d) for d in _iter_lines(text)]


def load_summaries(text: str) -> list[DailySummary]:
    return [summary_from_dict(d) for d in _iter_lines(text)]


def load_amls(text: str) -> list[AMLFinding]:
    return [aml_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "aml_from_dict",
    "aml_to_dict",
    "dump_amls",
    "dump_summaries",
    "dump_txns",
    "load_amls",
    "load_summaries",
    "load_txns",
    "summary_from_dict",
    "summary_to_dict",
    "txn_from_dict",
    "txn_to_dict",
]
