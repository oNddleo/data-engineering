"""Shared data types for 3-way wallet/merchant reconciliation.

The reconciler normalises three wallet-specific payloads — VNPay's
``vnp_*`` IPN columns, MoMo's ``partnerCode/orderId/transId/...``
fields, ZaloPay's ``app_trans_id/zp_trans_id/...`` — into a single
:class:`WalletTxn` shape that can be matched against a merchant order
ledger entry (:class:`MerchantOrder`).

Money is always stored as an integer VND amount; VND has no fractional
unit so we never need floats. Datetimes are always timezone-aware —
Vietnam is UTC+7 year-round, so all wallet timestamps that arrive as
naive strings get a ``+07:00`` tag at parse time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
"""Vietnam Standard Time (Indochina Time). No DST."""


class Wallet(str, Enum):
    """The three e-wallets this reconciler handles."""

    VNPAY = "VNPAY"
    MOMO = "MOMO"
    ZALOPAY = "ZALOPAY"


class Status(str, Enum):
    """Canonical transaction status after wallet-code normalisation."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


@dataclass(frozen=True, slots=True)
class WalletTxn:
    """One settlement-file row, normalised to a wallet-agnostic shape."""

    wallet: Wallet
    merchant_order_id: str
    wallet_txn_id: str
    amount_vnd: int
    status: Status
    paid_at: datetime
    bank_code: str | None = None
    raw_response_code: str = ""

    def __post_init__(self) -> None:
        if self.amount_vnd < 0:
            raise ValueError(f"amount_vnd must be >= 0, got {self.amount_vnd}")
        if not self.merchant_order_id:
            raise ValueError("merchant_order_id must be non-empty")
        if not self.wallet_txn_id:
            raise ValueError("wallet_txn_id must be non-empty")
        if self.paid_at.tzinfo is None:
            raise ValueError("paid_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class MerchantOrder:
    """One merchant-ledger order row — what the merchant *expects* to receive."""

    order_id: str
    wallet: Wallet
    expected_amount_vnd: int
    status: Status
    created_at: datetime

    def __post_init__(self) -> None:
        if self.expected_amount_vnd < 0:
            raise ValueError(f"expected_amount_vnd must be >= 0, got {self.expected_amount_vnd}")
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


__all__ = ["VN_TZ", "MerchantOrder", "Status", "Wallet", "WalletTxn"]
