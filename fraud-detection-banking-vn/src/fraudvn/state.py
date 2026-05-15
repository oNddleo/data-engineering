"""Per-account state store used by the fraud-detection engine.

The state we keep for each *initiator* account:

* ``prior_beneficiaries`` — the set of beneficiary accounts this
  initiator has ever transferred to. Used by the "new beneficiary"
  signal.
* ``recent_outgoing`` — a bounded deque of the last few outgoing
  transactions. Used by the velocity signal.

For each *beneficiary* account we additionally track:

* ``recent_incoming_sources`` — bounded deque of ``(source, timestamp)``
  tuples. Used by the "hot beneficiary" signal (many sources in a
  short window).

All deques are time-bounded — older entries are evicted lazily
inside the signal detectors. The state store itself doesn't time
out anything; it relies on the deque's `maxlen` to cap memory.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from fraudvn.schema import TransactionRequest


@dataclass(slots=True)
class AccountState:
    """All the per-account state the engine consults during evaluation."""

    account_id: str
    prior_beneficiaries: set[str] = field(default_factory=set)
    recent_outgoing: deque[tuple[str, datetime]] = field(default_factory=lambda: deque(maxlen=200))
    recent_incoming_sources: deque[tuple[str, datetime]] = field(
        default_factory=lambda: deque(maxlen=200)
    )


class StateStore:
    """In-memory account-state registry.

    Construct one per engine instance. Lookups are O(1); updates
    after a transaction are O(1) amortised because the underlying
    deques have a bounded ``maxlen``.
    """

    def __init__(self) -> None:
        self._states: dict[str, AccountState] = {}

    def __len__(self) -> int:
        return len(self._states)

    def get(self, account_id: str) -> AccountState:
        """Return (or lazily create) the state record for an account."""
        s = self._states.get(account_id)
        if s is None:
            s = AccountState(account_id=account_id)
            self._states[account_id] = s
        return s

    def all_account_ids(self) -> set[str]:
        return set(self._states)

    def record(self, txn: TransactionRequest) -> None:
        """Update both sides' state after a transaction is observed.

        Called by the engine *after* a decision is computed so the
        decision itself is based on pre-transaction state. We record
        unconditionally — even blocked transfers should age the
        velocity counter so consecutive identical attempts are
        rate-limited.
        """
        src = self.get(txn.initiator_account)
        src.prior_beneficiaries.add(txn.beneficiary_account)
        src.recent_outgoing.append((txn.beneficiary_account, txn.occurred_at))

        dst = self.get(txn.beneficiary_account)
        dst.recent_incoming_sources.append((txn.initiator_account, txn.occurred_at))


__all__ = ["AccountState", "StateStore"]
