"""Per-account, per-day transaction summaries.

Groups a stream of ``Transaction``s by ``(account, date)``. Date is
derived from the **local VN-time** of ``occurred_at`` — a transaction
at 23:30 UTC on 2026-05-18 (06:30 VN on 2026-05-19) is summarised
into 2026-05-19, matching the bank statement's day boundary.

REVERSED transactions are excluded from totals (they net to zero
economically), but counted in ``n_txns`` for audit completeness.
REJECTED transactions are excluded entirely (they never posted).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from vnbank.schema import DailySummary, TxnDirection, TxnKind, TxnStatus

if TYPE_CHECKING:
    from vnbank.schema import Transaction


def aggregate_daily(transactions: list[Transaction]) -> list[DailySummary]:
    """Aggregate transactions into per-account, per-day rollups.

    Output sorted by ``(date, account_number)``.
    """
    groups: dict[tuple[str, str, str], list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.status is TxnStatus.REJECTED:
            continue
        date = t.occurred_at.date().isoformat()
        groups[(t.account_number, t.bank_bin, date)].append(t)

    out: list[DailySummary] = []
    for (acct, bin_, date), txns in groups.items():
        n_txns = len(txns)
        # REVERSED is included in n_txns but excluded from totals.
        live = [t for t in txns if t.status is not TxnStatus.REVERSED]
        debits = [t for t in live if t.direction is TxnDirection.DEBIT]
        credits = [t for t in live if t.direction is TxnDirection.CREDIT]
        cash_deposits = [t for t in live if t.kind is TxnKind.CASH_DEPOSIT]
        cash_withdrawals = [t for t in live if t.kind is TxnKind.CASH_WITHDRAWAL]
        out.append(
            DailySummary(
                account_number=acct,
                bank_bin=bin_,
                date=date,
                n_txns=n_txns,
                total_debit_vnd=sum(t.amount_vnd for t in debits),
                total_credit_vnd=sum(t.amount_vnd for t in credits),
                n_cash_deposits=len(cash_deposits),
                cash_deposit_amount_vnd=sum(t.amount_vnd for t in cash_deposits),
                n_cash_withdrawals=len(cash_withdrawals),
                cash_withdrawal_amount_vnd=sum(t.amount_vnd for t in cash_withdrawals),
            )
        )
    out.sort(key=lambda s: (s.date, s.account_number))
    return out


__all__ = ["aggregate_daily"]
