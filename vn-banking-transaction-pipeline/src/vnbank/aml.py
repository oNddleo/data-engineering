"""AML signals — three patterns mandated by VN regulators.

* **Currency Transaction Report (CTR)** — Decree 87/2017/NĐ-CP +
  Circular 09/2017/TT-NHNN. Any single-day cash flow at or above
  300,000,000 VND must be reported to the SBV AML Department within
  one business day. We surface accounts whose daily cash totals
  cross that threshold.

* **Structuring** — splitting cash transactions into multiple deposits
  just under the CTR threshold to avoid the reporting trigger. A
  classic STR (Suspicious Transaction Report) pattern. We flag
  accounts with ≥ ``min_structuring_txns`` (default 3) cash deposits
  in a single day, none individually ≥ CTR, but summing to ≥ CTR.

* **Velocity** — abnormally high transfer count from a single account
  in a short window (e.g. funnel / money-mule pattern). Flag any
  account with ≥ ``min_velocity_txns`` (default 50) outbound transfers
  in a one-hour window.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING

from vnbank.schema import CTR_THRESHOLD_VND, TxnDirection, TxnKind, TxnStatus

if TYPE_CHECKING:
    from vnbank.schema import Transaction


class AMLKind(str, Enum):
    """Three AML signal types."""

    CTR_CASH_THRESHOLD = "CTR_CASH_THRESHOLD"
    STRUCTURING = "STRUCTURING"
    HIGH_VELOCITY = "HIGH_VELOCITY"


@dataclass(frozen=True, slots=True)
class AMLFinding:
    """One ops-actionable AML signal."""

    kind: AMLKind
    account_number: str
    bank_bin: str
    detail: str
    metric: int


def find_ctr(transactions: list[Transaction]) -> list[AMLFinding]:
    """Flag accounts with cash deposit OR withdrawal sums ≥ CTR threshold."""
    per_day: dict[tuple[str, str, str], int] = defaultdict(int)
    bin_by_account: dict[str, str] = {}
    for t in transactions:
        if t.status is not TxnStatus.POSTED:
            continue
        if t.kind not in {TxnKind.CASH_DEPOSIT, TxnKind.CASH_WITHDRAWAL}:
            continue
        date = t.occurred_at.date().isoformat()
        per_day[(t.account_number, t.bank_bin, date)] += t.amount_vnd
        bin_by_account[t.account_number] = t.bank_bin
    out: list[AMLFinding] = []
    for (acct, bin_, date), total in per_day.items():
        if total >= CTR_THRESHOLD_VND:
            out.append(
                AMLFinding(
                    kind=AMLKind.CTR_CASH_THRESHOLD,
                    account_number=acct,
                    bank_bin=bin_,
                    detail=f"cash flow {total:,} VND on {date}",
                    metric=total,
                )
            )
    out.sort(key=lambda f: (-f.metric, f.account_number))
    return out


def find_structuring(
    transactions: list[Transaction],
    *,
    min_structuring_txns: int = 3,
) -> list[AMLFinding]:
    """Flag suspected structuring: many sub-threshold cash deposits summing ≥ CTR."""
    if min_structuring_txns < 2:
        raise ValueError("min_structuring_txns must be >= 2")
    per_day: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for t in transactions:
        if t.status is not TxnStatus.POSTED:
            continue
        if t.kind is not TxnKind.CASH_DEPOSIT:
            continue
        if t.amount_vnd >= CTR_THRESHOLD_VND:
            continue  # not structuring — would already trigger CTR
        date = t.occurred_at.date().isoformat()
        per_day[(t.account_number, t.bank_bin, date)].append(t.amount_vnd)
    out: list[AMLFinding] = []
    for (acct, bin_, date), amounts in per_day.items():
        total = sum(amounts)
        if len(amounts) >= min_structuring_txns and total >= CTR_THRESHOLD_VND:
            out.append(
                AMLFinding(
                    kind=AMLKind.STRUCTURING,
                    account_number=acct,
                    bank_bin=bin_,
                    detail=(
                        f"{len(amounts)} sub-threshold deposits summing " f"{total:,} VND on {date}"
                    ),
                    metric=total,
                )
            )
    out.sort(key=lambda f: (-f.metric, f.account_number))
    return out


def find_high_velocity(
    transactions: list[Transaction],
    *,
    window_hours: int = 1,
    min_velocity_txns: int = 50,
) -> list[AMLFinding]:
    """Flag accounts with ≥ N outbound debits in any rolling ``window_hours`` span."""
    if window_hours < 1:
        raise ValueError("window_hours must be >= 1")
    if min_velocity_txns < 2:
        raise ValueError("min_velocity_txns must be >= 2")
    per_account: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.status is not TxnStatus.POSTED:
            continue
        if t.direction is not TxnDirection.DEBIT:
            continue
        per_account[(t.account_number, t.bank_bin)].append(t)
    delta = timedelta(hours=window_hours)
    out: list[AMLFinding] = []
    for (acct, bin_), txns in per_account.items():
        txns.sort(key=lambda x: x.occurred_at)
        # Sliding window over sorted timestamps.
        max_in_window = 0
        peak_end_idx = 0
        left = 0
        for right in range(len(txns)):
            while txns[right].occurred_at - txns[left].occurred_at > delta:
                left += 1
            count = right - left + 1
            if count > max_in_window:
                max_in_window = count
                peak_end_idx = right
        if max_in_window >= min_velocity_txns:
            peak_time = txns[peak_end_idx].occurred_at.isoformat()
            out.append(
                AMLFinding(
                    kind=AMLKind.HIGH_VELOCITY,
                    account_number=acct,
                    bank_bin=bin_,
                    detail=(
                        f"{max_in_window} debits in a {window_hours}h window " f"ending {peak_time}"
                    ),
                    metric=max_in_window,
                )
            )
    out.sort(key=lambda f: (-f.metric, f.account_number))
    return out


__all__ = [
    "AMLFinding",
    "AMLKind",
    "find_ctr",
    "find_high_velocity",
    "find_structuring",
]
