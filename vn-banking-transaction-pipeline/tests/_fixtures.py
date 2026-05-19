"""Test fixtures: transaction builders."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vnbank.schema import (
    VN_TZ,
    Transaction,
    TxnDirection,
    TxnKind,
    TxnStatus,
)

DEFAULT_TS = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)


def make_txn(**overrides: Any) -> Transaction:
    """Build a transaction with sensible defaults — override any field."""
    defaults: dict[str, Any] = {
        "txn_id": "T-0001",
        "account_number": "1234567890",
        "bank_bin": "970436",  # VCB
        "kind": TxnKind.INTRA_BANK_TRANSFER,
        "direction": TxnDirection.DEBIT,
        "amount_vnd": 100_000,
        "occurred_at": DEFAULT_TS,
        "status": TxnStatus.POSTED,
        "counterparty_account": "",
        "counterparty_bank_bin": "",
        "description": "",
    }
    defaults.update(overrides)
    return Transaction(**defaults)


__all__ = ["DEFAULT_TS", "make_txn"]
