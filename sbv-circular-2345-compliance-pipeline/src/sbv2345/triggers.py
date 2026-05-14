"""Stateful classifier that decides which Decision-2345 triggers apply.

The two value-based triggers (single-transaction and daily-cumulative)
are mutually exclusive *by construction* — the cumulative trigger
only fires for transactions ``<= 10M`` VND that, taken together with
the account's earlier transactions on the same UTC+7 day, would
push total daily volume past 20M VND. Large single transactions are
captured by the first trigger; small "bottom-of-stairs" transactions
that put the account past the cumulative threshold are captured by
the second.

The two non-value-based triggers stack independently on the value
ones.

The classifier maintains per-account, per-date running totals in a
plain dict. Production replaces that with Redis (the
``{account, day}`` key has 30-day TTL).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sbv2345.schema import AuditEvent, TriggerKind

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from sbv2345.schema import TransactionEvent


SINGLE_TXN_THRESHOLD = 10_000_000
DAILY_CUMULATIVE_THRESHOLD = 20_000_000

LEGAL_BASIS: dict[TriggerKind, str] = {
    TriggerKind.SINGLE_TXN_OVER_10M: "QĐ 2345/QĐ-NHNN Điều 1.1",
    TriggerKind.DAILY_CUMULATIVE_OVER_20M: "QĐ 2345/QĐ-NHNN Điều 1.2",
    TriggerKind.HIGH_RISK_BENEFICIARY: "Thông tư 35/2013/TT-NHNN — phòng chống rửa tiền",
    TriggerKind.INTERNATIONAL_TRANSFER: "Pháp lệnh Ngoại hối 2005, Điều 7",
}


class Classifier:
    """Map a stream of TransactionEvents to AuditEvents.

    Only transactions that fire at least one Decision-2345 trigger
    become AuditEvents. Transactions that fire nothing are silently
    skipped — they don't belong in the audit ledger, and including
    them would inflate retention costs.
    """

    def __init__(self, *, high_risk_accounts: Iterable[str] = ()) -> None:
        self._daily_total: dict[tuple[str, date], int] = {}
        self._high_risk: frozenset[str] = frozenset(high_risk_accounts)

    @property
    def high_risk_size(self) -> int:
        return len(self._high_risk)

    def classify(self, txn: TransactionEvent) -> AuditEvent | None:
        """Return an :class:`AuditEvent` if any trigger fires; else ``None``.

        Has side effect: updates the per-account daily-total counter
        so subsequent calls see this txn's contribution.
        """
        day = txn.occurred_at.date()
        key = (txn.initiator_account, day)
        prior = self._daily_total.get(key, 0)
        new_total = prior + txn.amount_vnd
        self._daily_total[key] = new_total

        triggers: list[TriggerKind] = []
        if txn.amount_vnd > SINGLE_TXN_THRESHOLD:
            triggers.append(TriggerKind.SINGLE_TXN_OVER_10M)
        elif new_total > DAILY_CUMULATIVE_THRESHOLD:
            triggers.append(TriggerKind.DAILY_CUMULATIVE_OVER_20M)
        if txn.beneficiary_account in self._high_risk:
            triggers.append(TriggerKind.HIGH_RISK_BENEFICIARY)
        if txn.cross_border:
            triggers.append(TriggerKind.INTERNATIONAL_TRANSFER)

        if not triggers:
            return None
        return AuditEvent(
            txn=txn,
            triggered_kinds=tuple(triggers),
            legal_bases=tuple(LEGAL_BASIS[t] for t in triggers),
            daily_cumulative_after_vnd=new_total,
        )

    def daily_total(self, account: str, day: date) -> int:
        """Inspect the running daily total — useful for audits + reports."""
        return self._daily_total.get((account, day), 0)


__all__ = [
    "DAILY_CUMULATIVE_THRESHOLD",
    "LEGAL_BASIS",
    "SINGLE_TXN_THRESHOLD",
    "Classifier",
]
