"""VN banking domain schema.

Models the core entities in a Vietnamese commercial banking pipeline:

* ``Bank``         — one commercial bank (BIN code, abbreviation, name)
* ``Account``      — one customer account at a bank
* ``Transaction``  — one debit/credit event with VN-specific kinds
* ``DailySummary`` — per-account, per-day rollup

All money is **integer VND** (no Decimal, no float drift — VN
domestic banking has no sub-units; receipts round to whole đồng).
All timestamps are tz-aware in ``VN_TZ`` (UTC+7).

NAPAS = National Payment Corporation of Vietnam, the central interbank
switch. NAPAS-247 is the 24/7 instant transfer rail (≤500M VND per
transaction since 2024). Transactions above that route via Citad
(Citizen Account Transfer & Inter-bank Debit, SBV's RTGS).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))

# Per Decree 87/2017/NĐ-CP + Circular 09/2017/TT-NHNN, cash transactions
# at or above 300,000,000 VND/day must be reported to SBV's AML unit (CTR).
CTR_THRESHOLD_VND = 300_000_000


class TxnKind(str, Enum):
    """Ten transaction kinds covering ~98% of retail-bank volume."""

    INTRA_BANK_TRANSFER = "INTRA_BANK_TRANSFER"  # sender + receiver same bank
    INTERBANK_TRANSFER = "INTERBANK_TRANSFER"  # via NAPAS-247 or Citad
    VIETQR_RECEIVE = "VIETQR_RECEIVE"  # QR-initiated credit
    VIETQR_SEND = "VIETQR_SEND"  # QR-initiated debit
    CASH_DEPOSIT = "CASH_DEPOSIT"  # at branch / ATM
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"  # at branch / ATM
    CARD_PURCHASE = "CARD_PURCHASE"  # POS / e-commerce
    BILL_PAYMENT = "BILL_PAYMENT"  # EVN, water, telco
    SALARY_CREDIT = "SALARY_CREDIT"  # employer payroll
    INTEREST = "INTEREST"  # accrued interest


class TxnStatus(str, Enum):
    """Lifecycle of one transaction."""

    PENDING = "PENDING"  # submitted, awaiting clearing
    POSTED = "POSTED"  # cleared & settled
    REVERSED = "REVERSED"  # successfully posted then refunded
    REJECTED = "REJECTED"  # failed before posting


class TxnDirection(str, Enum):
    """Sign convention from the account holder's perspective."""

    DEBIT = "DEBIT"  # money leaves the account
    CREDIT = "CREDIT"  # money enters the account


@dataclass(frozen=True, slots=True)
class Bank:
    """One commercial bank.

    ``bin_code`` is the 6-digit BIN allocated by NAPAS (e.g. 970436
    = Vietcombank, 970418 = BIDV). It appears as a prefix on cards and
    in interbank routing messages.
    """

    bin_code: str
    abbreviation: str
    name_vi: str
    name_en: str
    swift: str = ""
    account_length: int = 13  # most VN banks use 10-16 digit accounts

    def __post_init__(self) -> None:
        if not self.bin_code:
            raise ValueError("bin_code must be non-empty")
        if not self.bin_code.isdigit() or len(self.bin_code) != 6:
            raise ValueError(f"bin_code must be 6 digits, got {self.bin_code!r}")
        if not self.abbreviation:
            raise ValueError("abbreviation must be non-empty")
        if self.account_length < 4:
            raise ValueError(f"account_length must be >= 4, got {self.account_length}")


@dataclass(frozen=True, slots=True)
class Account:
    """One customer account at a VN bank."""

    account_number: str
    bank_bin: str
    holder_name: str
    currency: str = "VND"

    def __post_init__(self) -> None:
        if not self.account_number:
            raise ValueError("account_number must be non-empty")
        if not self.account_number.isdigit():
            raise ValueError(
                f"account_number must be all digits, got {self.account_number!r}",
            )
        if not self.bank_bin or not self.bank_bin.isdigit() or len(self.bank_bin) != 6:
            raise ValueError(f"bank_bin must be 6 digits, got {self.bank_bin!r}")
        if not self.holder_name:
            raise ValueError("holder_name must be non-empty")
        if self.currency not in {"VND", "USD", "EUR", "JPY"}:
            raise ValueError(f"unsupported currency {self.currency!r}")


@dataclass(frozen=True, slots=True)
class Transaction:
    """One debit/credit event on an account.

    For interbank transfers, ``counterparty_account`` and
    ``counterparty_bank_bin`` describe the *other* side of the move;
    for cash and interest events both are empty.
    """

    txn_id: str
    account_number: str
    bank_bin: str
    kind: TxnKind
    direction: TxnDirection
    amount_vnd: int  # always positive; sign comes from direction
    occurred_at: datetime
    status: TxnStatus = TxnStatus.POSTED
    counterparty_account: str = ""
    counterparty_bank_bin: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.txn_id:
            raise ValueError("txn_id must be non-empty")
        if not self.account_number:
            raise ValueError("account_number must be non-empty")
        if self.amount_vnd < 0:
            raise ValueError(f"amount_vnd must be >= 0, got {self.amount_vnd}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.counterparty_bank_bin and (
            not self.counterparty_bank_bin.isdigit() or len(self.counterparty_bank_bin) != 6
        ):
            raise ValueError(
                f"counterparty_bank_bin must be 6 digits, " f"got {self.counterparty_bank_bin!r}",
            )

    @property
    def signed_amount_vnd(self) -> int:
        """Positive for credits, negative for debits — for ledger math."""
        return self.amount_vnd if self.direction is TxnDirection.CREDIT else -self.amount_vnd


@dataclass(frozen=True, slots=True)
class DailySummary:
    """Per-account, per-day rollup."""

    account_number: str
    bank_bin: str
    date: str  # ISO YYYY-MM-DD
    n_txns: int
    total_debit_vnd: int
    total_credit_vnd: int
    n_cash_deposits: int
    cash_deposit_amount_vnd: int
    n_cash_withdrawals: int
    cash_withdrawal_amount_vnd: int

    def __post_init__(self) -> None:
        if self.total_debit_vnd < 0:
            raise ValueError("total_debit_vnd must be >= 0")
        if self.total_credit_vnd < 0:
            raise ValueError("total_credit_vnd must be >= 0")
        if self.cash_deposit_amount_vnd < 0:
            raise ValueError("cash_deposit_amount_vnd must be >= 0")
        if self.cash_withdrawal_amount_vnd < 0:
            raise ValueError("cash_withdrawal_amount_vnd must be >= 0")

    @property
    def net_flow_vnd(self) -> int:
        """Credits − debits."""
        return self.total_credit_vnd - self.total_debit_vnd


__all__ = [
    "CTR_THRESHOLD_VND",
    "VN_TZ",
    "Account",
    "Bank",
    "DailySummary",
    "Transaction",
    "TxnDirection",
    "TxnKind",
    "TxnStatus",
]
